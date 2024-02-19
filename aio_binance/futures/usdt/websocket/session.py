import asyncio

from aio_binance.futures.usdt import Client, WsClient
from loguru import logger


class WebsocketSession:
    """**WebSocket Session**
        Sets up user data flow, with auto key update
    See Also:
            https://binance-docs.github.io/apidocs/futures/en/#user-data-streams
    Args:
        client: Binance Api key.
        debug: info, debug, error. Default: debug
    Notes:
        - A User Data Stream listenKey is valid for 60 minutes after creation.
            This script will update it automatically
        - A single connection is only valid for 24 hours; expect to be disconnected at the 24-hour mark.
            It's better to run this script in a loop. And then it will reconnect automatically.
    Examples:
        import asyncio

        from aio_binance.futures.usdt.websocket.account import WebsocketSession

        from loguru import logger

        KEY = 'Key_Api_Binance'

        SECRET = 'Secret_Api_Binance'

        async def callback_event(data: dict):
            print(data)

        async def main():
            while True:
                async with WebsocketSession(client, debug='debug') as session:
                    await session.run('avaxusdt@depth@500ms', callback_event)
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            logger.info('Close Program Ctrl C')
    **Events:**
        **User Data Stream Expired:**
            When the listenKey used for the user data stream turns expired, this event will be pushed.

            **Notes:**
                - This event is not related to the websocket disconnection.
                - This event will be received only when a valid listenKey in connection got expired.
                - No more user data event will be updated after this event received until a new valid listenKey used.
            **Event Type:**
                {"e":"listenKeyExpired"}
    """

    def __init__(self,
                 client: Client,
                 debug: str = 'debug'):
        self.listen_key = None
        self.__api = client
        self.__debug = debug

    async def __aenter__(self):
        res = await self.__api.create_private_listen_key()
        self.listen_key = res['data']['listenKey']
        logger.log("ACCOUNT", '  listenKey add success  Connected')
        return self

    async def __aexit__(self, exc_type, exc, tb):
        logger.log("ACCOUNT", '  Close User Session')
        await self.__api.delete_private_listen_key()
        await asyncio.sleep(0.3)

    async def __update_key(self):
        """
        A User Data Stream is valid for 60 minutes after api.create_listen_key()
        Doing on a will extend its validity for 60 minutes.
        """
        sleep = 60*55  # 55 minutes
        first = True
        while True:
            if first:
                first = False
                await asyncio.sleep(sleep)
            await self.__api.update_private_listen_key()
            logger.log("ACCOUNT", f'  listen Key updated successfully. I will wait 55 min...')
            await asyncio.sleep(sleep)

    async def run(self, stream, callback_event: object):
        """**Run Session to receive events**

        Args:
            stream: stream name
            callback_event: Custom function where websocket messages will be processed.
        """
        done, _ = await asyncio.wait(
            [
                WsClient(self.listen_key,
                         debug=self.__debug)._listen_forever(stream, callback_event),
                self.__update_key()
            ],
            return_when=asyncio.FIRST_COMPLETED
        )
