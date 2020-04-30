import asyncio
import json
import aiohttp
from threading import Thread
import time

class Utility:

	def get_self_user(self):
		return User(asyncio.run(self.api_call(f"/users/@me", "GET")))

	def get_self_guilds(self):
		return [Guild(guild,self) for guild in asyncio.run(self.api_call(f"/users/@me/guilds", "GET"))]

	def send_message(self,channel,content):
		print(channel,content)
		return Message(asyncio.run(self.api_call(f"/channels/{channel}/messages", "POST", json={"content": content})),self)

	def get_guild(self,guild_id):
		return Guild(asyncio.run(self.api_call(f"/guilds/{guild_id}","GET")),self)

	def get_channel(self,channel_id):
		return Channel(asyncio.run(self.api_call(f"/channels/{channel_id}","GET")),self)

class Bot(Thread,Utility):

	def __init__(self,token):
		Thread.__init__(self)
		Utility.__init__(self)
		self.token=token
		self.url="https://discordapp.com/api"
		self.__last_sequence = ""
		self.events = {}

	def event(self,arg):
		def add_event(function):
			self.events[arg]=function
			def truc():...
			return truc
		return add_event

	async def api_call(self,path, method="GET", **kwargs):
		defaults = {
			"headers": {
				"Authorization": f"Bot {self.token}",
				"User-Agent": "Test Bot"
			}
		}
		kwargs = dict(defaults, **kwargs)
		async with aiohttp.ClientSession() as session:
			async with session.request(method, self.url+path,**kwargs) as response:
				try:
					assert 200 == response.status, response.reason
					return await response.json()
				except:...

	async def begin(self):
		response = await self.api_call("/gateway")
		await self.__main(response["url"])

	async def __main(self,url):
		events = {"MESSAGE_CREATE":["on_message",Message],"MESSAGE_REACTION_ADD":["reaction_add",Reaction]}
		async with aiohttp.ClientSession() as session:
			async with session.ws_connect(f"{url}?v=6&encoding=json") as ws:
				async for msg in ws:
					data = json.loads(msg.data)

					if data["op"] == 10:
						asyncio.create_task(self.__heartbeat(ws,data["d"]["heartbeat_interval"]))
						await ws.send_json({
							"op": 2,
							"d": {
								"token": self.token,
								"properties": {},
								"compress": False,
								"large_threshold": 250
						}})
					elif data["op"] == 0:
						if data["t"] in events:
							event = events[data["t"]]
							if event[0] in self.events:
								x = Thread(target=self.events[event[0]],args=(event[1](data["d"],self),))
								x.start()
						self.__last_sequence=data["s"]

	async def __heartbeat(self,ws, interval):
		while True:
			await asyncio.sleep(interval / 1000)
			await ws.send_json({"op": 1,"d": self.__last_sequence})

	def run(self):
		self.loop = asyncio.new_event_loop()
		try:
			self.loop.run_until_complete(self.begin())
		except RuntimeError:print("Bot éteint")

	def stop(self):
		try:
			self.loop.stop()
		except:...
		try:
			for x in asyncio.all_tasks():
				try:
					x.cancel()
				except:...
		except:...

class Guild:

	def __init__(self, guild, bot):
		self.id = guild["id"]
		self.name = guild["name"]
		#self.description = guild["description"]
		#self.emojis = [Emoji(emoji) for emoji in guild["emojis"]]
		self.__bot = bot

	def get_channels(self):
		channels = asyncio.run(self.__bot.api_call(f"/guilds/{self.id}/channels"))
		return [Channel(channel,self.__bot) for channel in channels]

class Channel:

	def __init__(self,channel,bot):
		self.id = channel["id"]
		self.type = channel["type"]
		self.name = channel["name"]
		self._guild = channel["guild_id"]
		self.__bot = bot

	def edit(self,modifs):
		asyncio.run(self.__bot.api_call(f"/channels/{self.id}","PATCH",json=modifs))

class Message:

	def __init__(self, message, bot):
		self.id = message["id"]
		self.content = message["content"]
		self.channel = message["channel_id"]
		self.author = User(message["author"])
		self.__bot = bot

	def delete(self):
		asyncio.run(self.__bot.api_call(f"/channels/{self.channel}/messages/{self.id}","DELETE"))

	def edit(self,content):
		asyncio.run(self.__bot.api_call(f"/channels/{self.channel}/messages/{self.id}","PATCH",json={"content": content}))

	def add_reaction(self, reaction):
		asyncio.run(self.__bot.api_call(f"/channels/{self.channel}/messages/{self.id}/reactions/{reaction}/@me","PUT"))

	def delete_reactions(self):
		asyncio.run(self.__bot.api_call(f"/channels/{self.channel}/messages/{self.id}/reactions","DELETE"))


class User:

	def __init__(self,user):
		self.id = user["id"]
		self.name = user["username"]
		self.discriminator = user["discriminator"]
		#self.avatar = f"https://cdn.discordapp.com/avatars/{self.id}/{user['avatar']}.png"

class Reaction:

	def __init__(self,reaction,bot):
		self.user = User(reaction["member"]["user"])
		self.channel = reaction["channel_id"]
		self.guild = reaction["guild_id"]
		self.emoji = Emoji(reaction["emoji"])
		self._message = reaction["message_id"]
		self.__bot = bot

	def get_message(self):
		return Message(asyncio.run(self.__bot.api_call(f"/channels/{self.channel}/messages/{self._message}")),self.__bot)

class Emoji:

	def __init__(self,emoji):
		self.name = emoji["name"]
		self.id = emoji["id"]