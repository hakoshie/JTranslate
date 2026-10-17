$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
$element = [System.Windows.Automation.AutomationElement]::FocusedElement
for ($depth = 0; $null -ne $element -and $depth -lt 8; $depth++) {
    if ($element.Current.IsPassword) {
        @{ status = 'none'; text = '' } | ConvertTo-Json -Compress
        exit
    }
    $pattern = $null
    if ($element.TryGetCurrentPattern([System.Windows.Automation.TextPattern]::Pattern, [ref]$pattern)) {
        $parts = @($pattern.GetSelection() | ForEach-Object { $_.GetText(-1) })
        @{ status = 'selected'; text = ($parts -join "`n") } | ConvertTo-Json -Compress
        exit
    }
    $element = [System.Windows.Automation.TreeWalker]::ControlViewWalker.GetParent($element)
}
@{ status = 'unsupported'; text = '' } | ConvertTo-Json -Compress
