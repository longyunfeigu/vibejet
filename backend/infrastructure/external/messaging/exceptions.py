class MessagingError(Exception):
    pass


class SerializationError(MessagingError):
    pass


class PublishError(MessagingError):
    pass


class ConsumeError(MessagingError):
    pass


class RequeueProducerFatalError(ConsumeError):
    """The consumer's retry/DLQ producer can never send again (fenced or fatal state).

    Raised out of AiokafkaConsumer.start() after the clients are closed; the cause is
    the aiokafka error. A fenced producer usually means two live consumers share one
    KAFKA__TRANSACTIONAL_ID.
    """


class RetryableError(MessagingError):
    pass


class NonRetryableError(MessagingError):
    pass
