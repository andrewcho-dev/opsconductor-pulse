# Branch Protection Settings

Configure these settings in GitHub repository settings:

## Main Branch Protection

1. Go to Settings > Branches > Add rule
2. Branch name pattern: `main`
3. Enable:
   - [x] Require a pull request before merging
   - [x] Require status checks to pass before merging
     - Required checks:
       - `Unit Tests`
       - `Integration Tests`
       - `Lint`
   - [x] Require branches to be up to date before merging
   - [x] Do not allow bypassing the above settings

## Develop Branch Protection (if used)

1. Branch name pattern: `develop`
2. Enable:
   - [x] Require status checks to pass before merging
     - Required checks:
       - `Unit Tests`
       - `Integration Tests`
