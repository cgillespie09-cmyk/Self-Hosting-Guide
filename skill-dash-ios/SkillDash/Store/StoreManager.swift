import StoreKit

/// Handles loading products and non-consumable purchases for cosmetic skins.
/// No consumables, no subscriptions, no randomized/gacha rewards — every
/// purchase is a one-time, transparently priced unlock.
@MainActor
final class StoreManager: ObservableObject {
    @Published private(set) var products: [Product] = []
    @Published private(set) var purchasedProductIDs: Set<String> = []
    @Published var equippedSkinID: String = UserDefaults.standard.string(forKey: "equippedSkinID") ?? "default" {
        didSet { UserDefaults.standard.set(equippedSkinID, forKey: "equippedSkinID") }
    }

    private var updatesTask: Task<Void, Never>?

    init() {
        updatesTask = listenForTransactionUpdates()
        Task {
            await loadProducts()
            await refreshPurchasedProducts()
        }
    }

    deinit {
        updatesTask?.cancel()
    }

    func loadProducts() async {
        do {
            products = try await Product.products(for: SkinCatalog.productIDs)
        } catch {
            print("Failed to load products: \(error)")
        }
    }

    func isUnlocked(_ skin: Skin) -> Bool {
        guard let productID = skin.productID else { return true }
        return purchasedProductIDs.contains(productID) || purchasedProductIDs.contains(SkinCatalog.bundleProductID)
    }

    func purchase(_ product: Product) async {
        do {
            let result = try await product.purchase()
            if case .success(let verification) = result,
               case .verified(let transaction) = verification {
                purchasedProductIDs.insert(transaction.productID)
                await transaction.finish()
            }
        } catch {
            print("Purchase failed: \(error)")
        }
    }

    func restorePurchases() async {
        try? await AppStore.sync()
        await refreshPurchasedProducts()
    }

    private func refreshPurchasedProducts() async {
        var purchased: Set<String> = []
        for await result in Transaction.currentEntitlements {
            if case .verified(let transaction) = result, transaction.revocationDate == nil {
                purchased.insert(transaction.productID)
            }
        }
        purchasedProductIDs = purchased
    }

    private func listenForTransactionUpdates() -> Task<Void, Never> {
        Task.detached { [weak self] in
            for await result in Transaction.updates {
                if case .verified(let transaction) = result {
                    await self?.refreshPurchasedProducts()
                    await transaction.finish()
                }
            }
        }
    }
}
