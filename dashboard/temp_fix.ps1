$content = Get-Content '__tests__/app/settings/notifications/page.test.tsx' -Raw
$content = $content -replace "screen\.getByText\('In-App'\)", "screen.getAllByText('In-App')[0]"
$content = $content -replace "screen\.getByText\('Browser Push'\)", "screen.getAllByText('Browser Push')[0]"
$content = $content -replace "screen\.getByText\('Email'\)", "screen.getAllByText('Email')[0]"
Set-Content '__tests__/app/settings/notifications/page.test.tsx' -Value $content -NoNewline
