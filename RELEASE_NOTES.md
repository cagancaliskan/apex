# Release v1.0.2 - Fix Strategy Panel Updates

**Release Date:** January 1, 2026

This patch release fixes a critical issue where the strategy panel would not update when selecting a driver.

## 🐛 Bug Fixes
- **Frontend**: Fixed logic error in `StrategyPanel` where it failed to look up the latest driver data from the selected driver object. Now correctly updates strategy recommendations for the selected driver.

**Full Changelog**: https://github.com/cagancaliskan/apex/compare/v1.0.1...v1.0.2
