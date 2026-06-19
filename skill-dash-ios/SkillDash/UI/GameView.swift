import SwiftUI
import SpriteKit

private final class GameSceneBridge: GameSceneDelegate {
    weak var state: GameState?
    init(state: GameState) { self.state = state }

    func gameDidUpdateScore(_ score: Int) {
        DispatchQueue.main.async { [weak state] in
            state?.score = score
        }
    }

    func gameDidEnd(finalScore: Int) {
        DispatchQueue.main.async { [weak state] in
            state?.endGame()
        }
    }
}

struct GameView: View {
    @EnvironmentObject var store: StoreManager
    @StateObject private var gameState = GameState()
    @State private var scene = makeScene()
    @State private var bridge: GameSceneBridge?

    var body: some View {
        ZStack {
            SpriteView(scene: scene)
                .ignoresSafeArea()

            VStack {
                HStack {
                    Text("Score: \(gameState.score)")
                        .font(.headline)
                        .padding(8)
                        .background(.ultraThinMaterial, in: Capsule())
                    Spacer()
                    Text("Best: \(gameState.bestScore)")
                        .font(.subheadline)
                        .padding(8)
                        .background(.ultraThinMaterial, in: Capsule())
                }
                .padding()
                Spacer()
            }

            if !gameState.isGameOver {
                HStack(spacing: 0) {
                    Color.clear.contentShape(Rectangle())
                        .onTapGesture { scene.moveLeft() }
                    Color.clear.contentShape(Rectangle())
                        .onTapGesture { scene.moveRight() }
                }
            }

            if gameState.isGameOver {
                GameOverView(score: gameState.score, bestScore: gameState.bestScore) {
                    startRun()
                }
            }
        }
        .onAppear {
            let newBridge = GameSceneBridge(state: gameState)
            bridge = newBridge
            scene.gameDelegate = newBridge
            startRun()
        }
    }

    private func startRun() {
        gameState.reset()
        gameState.isPlaying = true
        scene.skinColor = SKColor(SkinCatalog.skins.first(where: { $0.id == store.equippedSkinID })?.color ?? .blue)
        scene.startGame()
    }

    private static func makeScene() -> GameScene {
        let scene = GameScene()
        scene.scaleMode = .resizeFill
        return scene
    }
}
