"""Defines core consumer functionality"""
import logging

import confluent_kafka
from confluent_kafka import Consumer, OFFSET_BEGINNING
from confluent_kafka.avro import AvroConsumer,CachedSchemaRegistryClient
from confluent_kafka.avro.serializer import SerializerError
from tornado import gen


logger = logging.getLogger(__name__)


class KafkaConsumer:
    """
    Defines the base kafka consumer class
    """

    def __init__(
        self,
        topic_name_pattern,
        message_handler,
        is_avro=True,
        offset_earliest=False,
        sleep_secs=1.0,
        consume_timeout=0.1,
    ):
        """Creates a consumer object for asynchronous use"""
        self.topic_name_pattern = topic_name_pattern
        self.message_handler = message_handler
        self.sleep_secs = sleep_secs
        self.consume_timeout = consume_timeout
        self.offset_earliest = offset_earliest

        # Broker properties
        self.broker_properties = {
            "bootstrap.servers" : "localhost:9092",
            "group.id" : "my-consumer-group",
        }
        
        # Create the Consumer, using the appropriate type. Hardcoded, can be modified.
        if is_avro is True:
            self.broker_properties["schema.registry.url"] = "http://localhost:8081"         
            self.consumer = AvroConsumer(config = self.broker_properties)
        else:
            self.consumer = Consumer(self.broker_properties)

        # Subscribe to the topics.
        self.consumer.subscribe([self.topic_name_pattern], on_assign=self.on_assign)

    def on_assign(self, consumer, partitions):
        """
        Callback for when topic assignment takes place
        :param consumer: kafka consumer
        :param partitions: partitions for the topic
        :return:
        """
        # If the topic is configured to use `offset_earliest` set the partition offset to the beginning or earliest
        for partition in partitions:
            partition.offset = OFFSET_BEGINNING
            
        logger.info("partitions assigned for %s", self.topic_name_pattern)
        consumer.assign(partitions)

    async def consume(self):
        """
        Asynchronously consumes data from kafka topic
        """
        while True:
            num_results = 1
            while num_results > 0:
                num_results = self._consume()
            await gen.sleep(self.sleep_secs)

    def _consume(self):
        """
        Poll messages from kafka topic
        :return: 1 if message was received else 0
        """
        message = self.consumer.poll(1.0)
        if message is None:
            logger.info("No message received by consumer.")
            return 0
        elif message.error() is not None:
            logger.debug(f"error from consumer {message.error()}")
            return 0
        else:
            try:
                logger.info(message.value())
                return 1
            except KeyError as e:
                logger.info(f"Failed to unpack message {e}")
                return 0


    def close(self):
        """
        Cleanup the kafka consumer
        """
        self.consumer.close()
        logger.info("Shutting down consumer.")
