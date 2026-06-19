import SwiftUI

/// A simple math-problem gate that must be answered before the skin shop
/// becomes purchasable. No countdown, no pressure, no penalty for leaving.
struct ParentalGateView: View {
    let onPassed: () -> Void
    let onCancel: () -> Void

    @State private var a = Int.random(in: 4...9)
    @State private var b = Int.random(in: 4...9)
    @State private var answer: String = ""
    @State private var showError = false

    var body: some View {
        VStack(spacing: 20) {
            Text("Parents Only")
                .font(.title2).bold()
            Text("Ask a parent or guardian to answer this to continue to the shop.")
                .multilineTextAlignment(.center)
                .foregroundColor(.secondary)

            Text("\(a) × \(b) = ?")
                .font(.system(size: 36, weight: .bold, design: .rounded))

            TextField("Answer", text: $answer)
                .keyboardType(.numberPad)
                .textFieldStyle(.roundedBorder)
                .frame(width: 120)
                .multilineTextAlignment(.center)

            if showError {
                Text("That's not quite right. Try again.")
                    .foregroundColor(.red)
                    .font(.footnote)
            }

            HStack(spacing: 16) {
                Button("Cancel", role: .cancel, action: onCancel)
                Button("Continue") {
                    if Int(answer) == a * b {
                        onPassed()
                    } else {
                        showError = true
                        answer = ""
                        a = Int.random(in: 4...9)
                        b = Int.random(in: 4...9)
                    }
                }
                .buttonStyle(.borderedProminent)
            }
        }
        .padding(32)
    }
}
