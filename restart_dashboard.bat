@echo off
echo ========================================
echo DASHBOARD RESTART SCRIPT
echo ========================================
echo.

echo Stopping any running Next.js servers...
echo Please press Ctrl+C in any terminal windows running "npm run dev"
echo.
pause

echo.
echo Starting the Legacy Dashboard with the fix applied...
echo.

cd src\dashboard
echo Current directory: %CD%
echo.

echo Building the application to ensure latest changes...
call npm run build

echo.
echo Starting the development server...
echo The dashboard will be available at http://localhost:3000
echo.
echo IMPORTANT: After the server starts:
echo 1. Clear your browser cache (Ctrl+Shift+Delete)
echo 2. Navigate to http://localhost:3000
echo 3. Click "Performance Analytics" button
echo 4. You should now see the Performance Analytics page, NOT "coming soon"
echo.

call npm run dev