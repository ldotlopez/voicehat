class MessageNotMatched(Exception):
    """
    Raised if message cannot be "matched" with any registered plugin
    """


class SetupError(Exception):
    """
    Raised if plugin cannot be setup with given parameters
    """
