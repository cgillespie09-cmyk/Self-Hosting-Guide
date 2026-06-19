import SwiftUI

struct MainMenuView: View {
    @Binding var path: [RootView.Route]
    @EnvironmentObject var store: StoreManager

    private var equippedColor: Color {
        SkinCatalog.skins.first(where: { $0.id == store.equippedSkinID })?.color ?? .blue
    }

    var body: some View {
        VStack(spacing: 24) {
            Spacer()
            Text("Skill Dash")
                .font(.system(size: 48, weight: .heavy, design: .rounded))

            Circle()
                .fill(equippedColor)
                .frame(width: 80, height: 80)
                .overlay(Circle().stroke(.white, lineWidth: 3))

            Button {
                path.append(.game)
            } label: {
                Text("Play")
                    .font(.title2.bold())
                    .frame(maxWidth: 240)
                    .padding()
                    .background(Color.blue, in: Capsule())
                    .foregroundColor(.white)
            }

            Button {
                path.append(.store)
            } label: {
                Text("Skin Shop")
                    .frame(maxWidth: 240)
                    .padding()
                    .background(.ultraThinMaterial, in: Capsule())
            }

            Spacer()
            Text("No ads. No pay-to-win. Just skill.")
                .font(.footnote)
                .foregroundColor(.secondary)
        }
        .padding()
    }
}
