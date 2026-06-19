import Foundation

final class GameState: ObservableObject {
    @Published var score: Int = 0
    @Published var bestScore: Int = UserDefaults.standard.integer(forKey: "bestScore")
    @Published var isGameOver: Bool = false
    @Published var isPlaying: Bool = false

    func reset() {
        score = 0
        isGameOver = false
    }

    func endGame() {
        isPlaying = false
        isGameOver = true
        if score > bestScore {
            bestScore = score
            UserDefaults.standard.set(bestScore, forKey: "bestScore")
        }
        GameCenterManager.shared.submitScore(score)
    }
}
