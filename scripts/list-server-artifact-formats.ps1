param(
    [string]$Container = "aptitude-postgres",
    [string]$Database = "aptitude",
    [string]$User = "postgres"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Required command 'docker' was not found on PATH."
}

$query = @"
select
  s.id as skill_id,
  s.slug,
  v.version,
  c.media_type,
  encode(substring(c.payload from 1 for 4), 'hex') as magic_hex,
  case
    when c.media_type = 'application/zstd'
      and encode(substring(c.payload from 1 for 4), 'hex') = '28b52ffd'
      then 'tar.zst/current'
    else 'old/delete-candidate'
  end as artifact_format,
  c.storage_size_bytes
from skills s
join skill_versions v on v.skill_fk = s.id
join skill_contents c on c.id = v.content_fk
order by artifact_format, s.id, v.version;
"@

docker exec $Container psql -U $User -d $Database -c $query
