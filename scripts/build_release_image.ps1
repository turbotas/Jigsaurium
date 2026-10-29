param(
    [Parameter(Mandatory = $true)]
    [ValidatePattern('^v\d+\.\d+\.\d+$')]
    [string]$Version,

    [Parameter(Mandatory = $true)]
    [string]$Owner,

    [string]$ImageName = "jigsaurium",

    [string]$Platform = "linux/amd64"
)

$ErrorActionPreference = "Stop"

$shortSha = (git rev-parse --short=12 HEAD).Trim()
$fullSha = (git rev-parse HEAD).Trim()
$buildTime = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
$ownerLower = $Owner.ToLowerInvariant()
$image = "ghcr.io/$ownerLower/$ImageName"

"Building $image:$Version"
"Commit  : $fullSha"
"Built at: $buildTime"

docker login ghcr.io

docker buildx build --platform $Platform `
  --build-arg APP_VERSION=$Version `
  --build-arg APP_BUILD_SHA=$fullSha `
  --build-arg APP_BUILD_TIME=$buildTime `
  -t "$image:$Version" `
  -t "$image:sha-$shortSha" `
  --push .

if ($LASTEXITCODE -ne 0) {
    throw "Docker buildx build failed."
}

"Release image pushed: $image:$Version"
"SHA tag pushed      : $image:sha-$shortSha"
