import SwiftUI

struct Skin: Identifiable, Equatable {
    let id: String
    let displayName: String
    let color: Color
    /// nil for the free default skin
    let productID: String?
}

/// All skins are cosmetic color changes only. None of them affect lane
/// width, fall speed, hitbox size, or scoring, so purchasing never gives
/// a gameplay advantage.
enum SkinCatalog {
    static let neonID = "com.example.skilldash.skin.neon"
    static let crimsonID = "com.example.skilldash.skin.crimson"
    static let forestID = "com.example.skilldash.skin.forest"
    static let goldID = "com.example.skilldash.skin.gold"
    static let bundleProductID = "com.example.skilldash.bundle.allskins"

    static let productIDs = [neonID, crimsonID, forestID, goldID, bundleProductID]

    static let skins: [Skin] = [
        Skin(id: "default", displayName: "Classic", color: .blue, productID: nil),
        Skin(id: "neon", displayName: "Neon", color: .cyan, productID: neonID),
        Skin(id: "crimson", displayName: "Crimson", color: .red, productID: crimsonID),
        Skin(id: "forest", displayName: "Forest", color: .green, productID: forestID),
        Skin(id: "gold", displayName: "Gold", color: .yellow, productID: goldID),
    ]
}
