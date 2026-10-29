param(
    [Parameter(Mandatory = $true)]
    [string]$Owner,

    [Parameter(Mandatory = $true)]
    [ValidateSet("dev", "test", "prod")]
    [string]$Pointer,

    [Parameter(Mandatory = $true)]
    [string]$SourceRef,

    [string]$ImageName = "jigsaurium"
)

$ErrorActionPreference = "Stop"

$ownerLower = $Owner.ToLowerInvariant()
$image = "ghcr.io/$ownerLower/$ImageName"

if ($SourceRef.StartsWith("sha256:")) {
    $sourceImage = "$image@$SourceRef"
} else {
    $sourceImage = "$image:$SourceRef"
}

"Promoting $sourceImage -> $image:$Pointer"

docker login ghcr.io
docker buildx imagetools create -t "$image:$Pointer" "$sourceImage"

if ($LASTEXITCODE -ne 0) {
    throw "Promotion failed."
}

"Promotion completed: $image:$Pointer"
