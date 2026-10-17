$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$element = [System.Windows.Automation.AutomationElement]::FocusedElement
$editable = $null -ne $element -and $element.Current.ControlType -eq [System.Windows.Automation.ControlType]::Edit
for ($depth = 0; $null -ne $element -and $depth -lt 8; $depth++) {
    if ($element.Current.IsPassword) {
        @{ status = 'blocked'; text = ''; copy_safe = $false } | ConvertTo-Json -Compress
        exit
    }
    $pattern = $null
    if ($element.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$pattern)) {
        $parts = @($pattern.GetSelection() | ForEach-Object { $_.GetText(-1) })
        @{ status = 'selected'; text = ($parts -join "`n"); copy_safe = -not $editable } | ConvertTo-Json -Compress
        exit
    }
    $element = [System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($element)
}
@{ status = 'unsupported'; text = ''; copy_safe = -not $editable } | ConvertTo-Json -Compress
