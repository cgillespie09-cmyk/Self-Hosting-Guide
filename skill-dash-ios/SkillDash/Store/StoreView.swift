import SwiftUI
import StoreKit

struct StoreView: View {
    @EnvironmentObject var store: StoreManager
    @State private var passedGate = false

    var body: some View {
        Group {
            if passedGate {
                shopContent
            } else {
                ParentalGateView(onPassed: { passedGate = true }, onCancel: { passedGate = false })
            }
        }
    }

    private var shopContent: some View {
        ScrollView {
            VStack(spacing: 16) {
                Text("Skin Shop")
                    .font(.largeTitle).bold()
                Text("All skins are cosmetic only — they don't change how the game plays. Everyone competes on the same leaderboard.")
                    .font(.footnote)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal)

                ForEach(SkinCatalog.skins) { skin in
                    SkinRow(skin: skin)
                }

                Button("Restore Purchases") {
                    Task { await store.restorePurchases() }
                }
                .padding(.top)
            }
            .padding()
        }
    }
}

private struct SkinRow: View {
    let skin: Skin
    @EnvironmentObject var store: StoreManager

    private var product: Product? {
        store.products.first { $0.id == skin.productID }
    }

    var body: some View {
        HStack {
            Circle()
                .fill(skin.color)
                .frame(width: 44, height: 44)
            VStack(alignment: .leading) {
                Text(skin.displayName).bold()
                if store.equippedSkinID == skin.id {
                    Text("Equipped").font(.caption).foregroundColor(.secondary)
                }
            }
            Spacer()
            if store.isUnlocked(skin) {
                Button(store.equippedSkinID == skin.id ? "Equipped" : "Equip") {
                    store.equippedSkinID = skin.id
                }
                .disabled(store.equippedSkinID == skin.id)
            } else if let product {
                Button(product.displayPrice) {
                    Task { await store.purchase(product) }
                }
                .buttonStyle(.borderedProminent)
            } else {
                ProgressView()
            }
        }
    }
}
