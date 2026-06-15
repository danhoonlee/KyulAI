import random
import torch
from torch.nn import Module, ModuleList, Linear
from torch.nn import functional

from coral_pytorch.layers import CoralLayer
import sparsemax


# SimpleMLP for JointMLP original model
class SimpleMLP(Module):
    def __init__(
        self, input_size: int, hidden_size: int, num_layers: int, layer_size: int
    ):
        super(SimpleMLP, self).__init__()
        # self.layer_size = layer_size

        self.num_layers = num_layers
        self.layer_input_num = [layer_size for _ in range(self.num_layers)]
        layer_output_num = [layer_size for _ in range(self.num_layers)]
        layer_output_num[-1] = input_size
        self.layer_output_num = layer_output_num

        self._input_layer = torch.nn.Linear(input_size, self.layer_input_num[0])

        self._layers = ModuleList(
            [
                torch.nn.Linear(self.layer_input_num[i], self.layer_output_num[i])
                for i in range(self.num_layers)
            ]
        )

        self._out_reg_layer = torch.nn.Linear(
            self.layer_output_num[len(self.layer_output_num) - 1], hidden_size
        )

        self.prior = torch.ones(layer_size)
        self.selector = sparsemax.Sparsemax(dim=-1)

    def forward(self, features):
        p = random.randint(1, 2) / 10
        features = functional.dropout(features, p=p, training=self.training)

        x = self._input_layer(features)
        x = functional.leaky_relu(x)

        device = next(self.parameters()).device
        x = torch.mul(x, self.prior.to(device))
        x = self.selector(x)

        for layer in self._layers:
            x = layer(x)
            x = functional.leaky_relu(x)

        reg = self._out_reg_layer(x)
        return reg


# JointMLP for the original model
class JointmLP(Module):
    def __init__(
        self,
        input_size: int,
        hidden_size: int,
        num_nets: int,
        num_classes: int,
        num_layers: int,
        layer_size: int,
    ):
        super(JointmLP, self).__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_nets = num_nets
        self.num_classes = num_classes
        self.num_layers = num_layers
        self.layer_size = layer_size

        self._mlps = ModuleList(
            [
                SimpleMLP(
                    self.input_size, self.hidden_size, self.num_layers, self.layer_size
                )
                for _ in range(self.num_nets)
            ]
        )

        # Output Layer -> Reg(1) + CORAL(num_classes)
        # Regression
        self.output_layer_reg = Linear(self.num_nets * self.num_classes, 1)

        # Coral
        self.output_layer_class = CoralLayer(
            size_in=self.num_nets * self.num_classes, num_classes=self.num_classes
        )

    def forward(self, features):
        outs = [mlp(features) for mlp in self._mlps]
        outs = torch.cat(outs, dim=2)

        outs_reg = self.output_layer_reg(outs)
        outs_class = self.output_layer_class(outs)

        outs = torch.cat([outs_reg, outs_class], dim=2)

        return outs
