# GitHub Setup Instructions

## Commands to Push Your Code

Replace `YOUR_USERNAME` with your actual GitHub username:

```bash
# Add the GitHub remote
git remote add origin https://github.com/YOUR_USERNAME/autopassgui.git

# Push to GitHub
git push -u origin main
```

## After Pushing

1. Go to your repository on GitHub: `https://github.com/YOUR_USERNAME/autopassgui`
2. Click on the **"Actions"** tab
3. You should see the "Build App" workflow running automatically
4. Wait for the build to complete (takes about 5-10 minutes)

## Download Built Packages

Once the build completes:

1. Click on the completed workflow run
2. Scroll down to **"Artifacts"** section
3. Download:
   - **windows-installer** - Contains the `.msi` file for Windows
   - **linux-deb** - Contains the `.deb` file for Linux

## Important Notes

- The workflow runs automatically on every push to the `main` branch
- Windows builds will create `.msi` installer files
- Linux builds will create `.deb` package files
- Both will be available as downloadable artifacts for 90 days

## Triggering Manual Builds

You can also trigger builds manually:

1. Go to the **Actions** tab
2. Select **"Build App"** workflow
3. Click **"Run workflow"** button
4. Select the `main` branch
5. Click **"Run workflow"**
