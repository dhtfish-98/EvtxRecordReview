# Validation only: fixed offline EVTX -> native XML -> bounded numeric JSON facts.
# No live channel/session, FormatDescription, message DLL rendering or raw XML output.
param([Parameter(Mandatory=$true)][string]$InputPath)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$reader = $null
$stage = 'reader'
try {
    Add-Type -AssemblyName System.Core
    $query = [System.Diagnostics.Eventing.Reader.EventLogQuery]::new(
        $InputPath, [System.Diagnostics.Eventing.Reader.PathType]::FilePath)
    $query.TolerateQueryErrors = $false
    $query.ReverseDirection = $false
    $reader = [System.Diagnostics.Eventing.Reader.EventLogReader]::new($query)
    $count = 0
    while ($null -ne ($record = $reader.ReadEvent())) {
        try {
            $count++
            if ($count -gt 2048) { throw 'native_record_budget' }
            $stage = 'xml_render'
            $xml = $record.ToXml()
            if ($xml.Length -gt 262144) { throw 'native_xml_budget' }
            $settings = [System.Xml.XmlReaderSettings]::new()
            $settings.DtdProcessing = [System.Xml.DtdProcessing]::Prohibit
            $settings.XmlResolver = $null
            $settings.MaxCharactersInDocument = 262144
            $settings.MaxCharactersFromEntities = 0
            $textReader = [System.IO.StringReader]::new($xml)
            $xmlReader = [System.Xml.XmlReader]::Create($textReader, $settings)
            $stage = 'bounded_xml_parse'
            try {
                $document = [System.Xml.XmlDocument]::new()
                $document.XmlResolver = $null
                $document.Load($xmlReader)
            } finally {
                $xmlReader.Dispose()
                $textReader.Dispose()
            }
            $namespaces = [System.Xml.XmlNamespaceManager]::new($document.NameTable)
            $namespaces.AddNamespace('e', 'http://schemas.microsoft.com/win/2004/08/events/event')
            $fields = [ordered]@{}
            $stage = 'numeric_fields'
            foreach ($name in @('EventID','EventRecordID','Version','Level','Task','Opcode')) {
                $nodes = $document.SelectNodes("/e:Event/e:System/e:$name", $namespaces)
                if ($nodes.Count -gt 1) { throw 'native_duplicate_numeric_field' }
                if ($nodes.Count -eq 1) {
                    $value = $nodes[0].InnerText
                    if ($value.Length -gt 20 -or $value -notmatch '^[0-9]+$') {
                        throw 'native_numeric_field_invalid'
                    }
                    $fields[$name] = $value
                }
            }
            if ($null -eq $record.RecordId -or $null -eq $record.TimeCreated) {
                throw 'native_identity_missing'
            }
            $stage = 'identity'
            $row = [ordered]@{
                record_identifier = $record.RecordId.ToString([System.Globalization.CultureInfo]::InvariantCulture)
                filetime_ticks = $record.TimeCreated.ToUniversalTime().ToFileTimeUtc().ToString(
                    [System.Globalization.CultureInfo]::InvariantCulture)
                fields = $fields
            }
            $line = ConvertTo-Json -InputObject $row -Depth 3 -Compress
            if ($line.Length -gt 4096) { throw 'native_json_budget' }
            [Console]::Out.WriteLine($line)
            $stage = 'reader'
        } finally {
            $record.Dispose()
        }
    }
} catch {
    [Console]::Error.WriteLine('native_offline_export_failed:' + $stage)
    exit 1
} finally {
    if ($null -ne $reader) { $reader.Dispose() }
}
