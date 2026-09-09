from roman_coin_app.schemas import CoinImages, IdentificationResult

class IdentificationService:
    def __init__(self, multimodal_provider):
        self.provider=multimodal_provider
    def identify(self, images: CoinImages) -> IdentificationResult:
        return self.provider.identify(
            obverse_bytes=images.obverse_bytes,
            reverse_bytes=images.reverse_bytes,
            obverse_mime=images.obverse_mime,
            reverse_mime=images.reverse_mime,
        )
