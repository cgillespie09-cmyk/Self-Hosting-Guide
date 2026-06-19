import GameKit

/// Submits scores to a single global leaderboard. Skins never factor into
/// score, so paying and non-paying players compete on equal footing.
final class GameCenterManager {
    static let shared = GameCenterManager()
    static let leaderboardID = "com.example.skilldash.leaderboard"

    private var isAuthenticated = false

    func authenticate() {
        GKLocalPlayer.local.authenticateHandler = { [weak self] _, error in
            self?.isAuthenticated = (error == nil)
        }
    }

    func submitScore(_ score: Int) {
        guard isAuthenticated else { return }
        Task {
            try? await GKLeaderboard.submitScore(
                score,
                context: 0,
                player: GKLocalPlayer.local,
                leaderboardIDs: [Self.leaderboardID]
            )
        }
    }
}
