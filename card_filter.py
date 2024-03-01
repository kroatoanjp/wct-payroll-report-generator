class CardFilter:
    def matches(self, card):
        raise NotImplementedError

class NameStartsWith(CardFilter):
    def __init__(self, keyword):
        self._keyword = keyword

    def matches(self, card):
        return card.name.startswith(self._keyword)

class NameContains(CardFilter):
    def __init__(self, keyword):
        self._keyword = keyword

    def matches(self, card):
        return self._keyword in card.name