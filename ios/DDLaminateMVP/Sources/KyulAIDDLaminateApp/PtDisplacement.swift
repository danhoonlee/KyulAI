import KyulAIDDLaminateCore

extension Array where Element == ResponseCurvePoint {
    func displacement(atForce targetForce: Double?) -> Double? {
        guard let targetForce, targetForce.isFinite, let first else {
            return nil
        }
        if targetForce <= first.force {
            return first.displacement
        }
        for index in 1..<count {
            let previous = self[index - 1]
            let current = self[index]
            let low = Swift.min(previous.force, current.force)
            let high = Swift.max(previous.force, current.force)
            guard targetForce >= low, targetForce <= high else {
                continue
            }
            let forceDelta = current.force - previous.force
            guard forceDelta != 0 else {
                return current.displacement
            }
            let ratio = (targetForce - previous.force) / forceDelta
            return previous.displacement + ratio * (current.displacement - previous.displacement)
        }
        return last?.displacement
    }
}

extension ResponsePredictionResult {
    var predictedPtDisplacement: Double? {
        curve.displacement(atForce: predictedPt)
    }
}

extension DDLaminateRecentRun {
    var predictedPtDisplacement: Double? {
        curve.displacement(atForce: predictedPt)
    }
}
