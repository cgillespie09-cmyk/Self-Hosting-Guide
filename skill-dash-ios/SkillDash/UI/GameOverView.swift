import SwiftUI

struct GameOverView: View {
    let score: Int
    let bestScore: Int
    let onPlayAgain: () -> Void

    @EnvironmentObject var store: StoreManager
    @State private var showStore = false

    var body: some View {
        VStack(spacing: 20) {
            Text("Game Over")
                .font(.largeTitle).bold()
            Text("Score: \(score)")
                .font(.title2)
            if score >= bestScore && score > 0 {
                Text("New Best!").foregroundColor(.yellow).bold()
            }
            Button("Play Again", action: onPlayAgain)
                .buttonStyle(.borderedProminent)
            Button("Skin Shop") { showStore = true }
        }
        .padding(32)
        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 24))
        .padding()
        .sheet(isPresented: $showStore) {
            StoreView()
                .environmentObject(store)
        }
    }
}
