# input: 无
# output: MessagingError 及子类：SerializationError / PublishError / ConsumeError / RequeueProducerFatalError / RetryableError / NonRetryableError
# owner: unknown
# pos: 基础设施层 - 消息模块异常（handler 用 Retryable/NonRetryable 决定重试或进 DLQ）；一旦我被更新，务必更新我的开头注释以及所属文件夹的md
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
