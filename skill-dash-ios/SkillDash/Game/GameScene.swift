import SpriteKit

protocol GameSceneDelegate: AnyObject {
    func gameDidUpdateScore(_ score: Int)
    func gameDidEnd(finalScore: Int)
}

/// Lane-dodge arcade game. Skin color is purely cosmetic and has no effect
/// on lane width, fall speed, hitbox size, or scoring — every player,
/// paying or not, plays the exact same game.
final class GameScene: SKScene, SKPhysicsContactDelegate {
    weak var gameDelegate: GameSceneDelegate?
    var skinColor: SKColor = .systemBlue

    private let laneCount = 3
    private var laneXPositions: [CGFloat] = []
    private var currentLane = 1

    private var player: SKShapeNode!
    private var lastUpdateTime: TimeInterval = 0
    private var elapsed: TimeInterval = 0
    private var spawnTimer: TimeInterval = 0
    private var spawnInterval: TimeInterval = 1.1
    private var fallSpeed: CGFloat = 220
    private var score = 0
    private var isGameActive = false

    private let obstacleCategory: UInt32 = 0x1 << 0
    private let coinCategory: UInt32 = 0x1 << 1
    private let playerCategory: UInt32 = 0x1 << 2

    override func didMove(to view: SKView) {
        backgroundColor = SKColor(red: 0.05, green: 0.07, blue: 0.12, alpha: 1)
        physicsWorld.gravity = .zero
        physicsWorld.contactDelegate = self
        layoutLanes()
        startGame()
    }

    override func didChangeSize(_ oldSize: CGSize) {
        layoutLanes()
        if let player = player {
            player.position = CGPoint(x: laneXPositions[currentLane], y: player.position.y)
        }
    }

    private func layoutLanes() {
        guard size.width > 0 else { return }
        laneXPositions = (0..<laneCount).map { i in
            size.width * (CGFloat(i) + 0.5) / CGFloat(laneCount)
        }
    }

    private func spawnPlayer() {
        player?.removeFromParent()
        let node = SKShapeNode(circleOfRadius: 22)
        node.fillColor = skinColor
        node.strokeColor = .white
        node.lineWidth = 2
        node.zPosition = 10
        let x = laneXPositions.isEmpty ? size.width / 2 : laneXPositions[currentLane]
        node.position = CGPoint(x: x, y: size.height * 0.18)
        let body = SKPhysicsBody(circleOfRadius: 22)
        body.isDynamic = false
        body.categoryBitMask = playerCategory
        body.contactTestBitMask = obstacleCategory | coinCategory
        body.collisionBitMask = 0
        node.physicsBody = body
        addChild(node)
        player = node
    }

    func startGame() {
        removeAllChildren()
        score = 0
        elapsed = 0
        spawnTimer = 0
        spawnInterval = 1.1
        fallSpeed = 220
        currentLane = 1
        lastUpdateTime = 0
        isGameActive = true
        layoutLanes()
        spawnPlayer()
    }

    func moveLeft() {
        guard isGameActive else { return }
        currentLane = max(0, currentLane - 1)
        movePlayerToCurrentLane()
    }

    func moveRight() {
        guard isGameActive else { return }
        currentLane = min(laneCount - 1, currentLane + 1)
        movePlayerToCurrentLane()
    }

    private func movePlayerToCurrentLane() {
        let action = SKAction.moveTo(x: laneXPositions[currentLane], duration: 0.12)
        action.timingMode = .easeOut
        player.run(action)
    }

    override func update(_ currentTime: TimeInterval) {
        guard isGameActive else { lastUpdateTime = 0; return }
        if lastUpdateTime == 0 { lastUpdateTime = currentTime }
        let dt = currentTime - lastUpdateTime
        lastUpdateTime = currentTime
        elapsed += dt
        spawnTimer += dt

        fallSpeed = 220 + CGFloat(min(elapsed, 60)) * 4
        spawnInterval = max(0.45, 1.1 - elapsed * 0.01)

        if spawnTimer >= spawnInterval {
            spawnTimer = 0
            spawnFallingNode()
        }

        for node in children where node.name == "obstacle" || node.name == "coin" {
            node.position.y -= fallSpeed * CGFloat(dt)
            if node.position.y < -40 {
                node.removeFromParent()
            }
        }

        score += Int(dt * 10)
        gameDelegate?.gameDidUpdateScore(score)
    }

    private func spawnFallingNode() {
        guard !laneXPositions.isEmpty else { return }
        let lane = Int.random(in: 0..<laneCount)
        let isCoin = Int.random(in: 0..<4) == 0
        let node = SKShapeNode(circleOfRadius: isCoin ? 10 : 18)
        node.position = CGPoint(x: laneXPositions[lane], y: size.height + 40)
        node.name = isCoin ? "coin" : "obstacle"
        node.fillColor = isCoin ? .systemYellow : .systemRed
        node.strokeColor = .white
        node.lineWidth = 1.5
        let body = SKPhysicsBody(circleOfRadius: isCoin ? 10 : 18)
        body.isDynamic = false
        body.categoryBitMask = isCoin ? coinCategory : obstacleCategory
        body.contactTestBitMask = playerCategory
        body.collisionBitMask = 0
        node.physicsBody = body
        addChild(node)
    }

    private func endGame() {
        guard isGameActive else { return }
        isGameActive = false
        gameDelegate?.gameDidEnd(finalScore: score)
    }

    func didBegin(_ contact: SKPhysicsContact) {
        let names = [contact.bodyA.node?.name, contact.bodyB.node?.name]
        if names.contains("obstacle") {
            endGame()
        } else if names.contains("coin") {
            let coinNode = contact.bodyA.node?.name == "coin" ? contact.bodyA.node : contact.bodyB.node
            coinNode?.removeFromParent()
            score += 25
        }
    }
}
