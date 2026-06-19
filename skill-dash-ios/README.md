# Skill Dash

A one-thumb lane-dodge arcade game for iOS, built with SwiftUI + SpriteKit.

## Design principles (please keep these if you extend the game)

- **No pay-to-win.** Skins are color-only cosmetics. They never change lane
  width, fall speed, hitbox size, or scoring. Everyone competes on one
  Game Center leaderboard regardless of what they've bought.
- **No ads, no loot boxes, no gacha.** Every purchase is a one-time,
  transparently priced non-consumable (`Product.products` / StoreKit 2).
  No randomized rewards, no consumable currency, no subscriptions.
- **No dark patterns.** No countdown timers, no fake scarcity, no nagging
  purchase prompts, no penalty for declining or cancelling.
- **Parental gate.** The skin shop is hidden behind `ParentalGateView`
  (a simple math problem) before any purchase button is reachable.
  `Products.storekit` also has `_askToBuyEnabled: true`, which complements
  this with Apple's own Ask to Buy / Family Sharing approval flow when
  testing under a Family Sharing organizer account.
- **No third-party SDKs, no tracking, no ads network.** Only Apple
  frameworks are used (SwiftUI, SpriteKit, StoreKit, GameKit), which keeps
  this easy to make COPPA/App Store kids-category compliant.

## Project layout

```
skill-dash-ios/
  project.yml                  XcodeGen spec (generates the .xcodeproj)
  SkillDash/
    App/SkillDashApp.swift     App entry point
    Game/
      GameScene.swift          SpriteKit gameplay (lane dodge, scoring)
      GameState.swift          Score/best-score state for SwiftUI
      GameCenterManager.swift  Leaderboard auth + score submission
    Store/
      SkinCatalog.swift        Skin definitions (cosmetic only)
      StoreManager.swift       StoreKit 2 product loading + purchases
      ParentalGateView.swift   Math-problem gate before the shop
      StoreView.swift          Skin shop UI
    UI/
      RootView.swift, MainMenuView.swift, GameView.swift, GameOverView.swift
    Resources/
      Assets.xcassets          App icon slot (placeholder, add real art)
      Products.storekit        Local StoreKit testing configuration
```

## Building (requires a Mac with Xcode — this project was scaffolded in a
Linux container, so it has **not** been compiled or run yet)

1. Install [XcodeGen](https://github.com/yonaskolb/XcodeGen) if you don't
   have it: `brew install xcodegen`
2. From this folder, generate the Xcode project:
   ```
   xcodegen generate
   ```
3. Open `SkillDash.xcodeproj` in Xcode.
4. In **Signing & Capabilities**:
   - Set your Team and a real bundle identifier (replace the
     `com.example.skilldash` placeholder everywhere — see below).
   - Add the **Game Center** capability.
   - Add the **In-App Purchase** capability.
5. To test purchases locally without App Store Connect: **Product > Scheme
   > Edit Scheme > Run > Options**, set **StoreKit Configuration** to
   `SkillDash/Resources/Products.storekit`.
6. Build and run on a simulator or device.

### Replacing the placeholder bundle ID / product IDs

Search the project for `com.example.skilldash` and replace it with your
real reverse-DNS identifier in:
- `project.yml` (`PRODUCT_BUNDLE_IDENTIFIER`, `bundleIdPrefix`)
- `SkillDash/Store/SkinCatalog.swift` (product IDs)
- `SkillDash/Resources/Products.storekit` (`productID` fields)
- `SkillDash/Game/GameCenterManager.swift` (`leaderboardID`)

Then create matching In-App Purchase products and a leaderboard in App
Store Connect with the same identifiers before shipping.

## App Store kids-category notes

If you submit this under the **Kids Category**, Apple requires (among
other things): no third-party analytics/ads SDKs (this project has none),
a privacy policy, and any purchases or external links gated appropriately
(handled here via `ParentalGateView`). Review Apple's current Kids
Category guidelines before submission, as requirements change.

## What's not done yet

- App icon and in-game art are placeholders/programmatic shapes — no
  real artwork has been created.
- Game Center leaderboard and IAP products need to be created in App
  Store Connect with matching identifiers before real purchases work.
- The project has not been compiled — do a build pass in Xcode and fix
  any straightforward syntax issues before relying on it.
