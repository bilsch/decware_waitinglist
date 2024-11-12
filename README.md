# decware_waitinglist

This is a very basic scraper for [decware](https://www.decwareproducts.com/) order list. They provide this list for folks to use so ;) 

Please be kind to decware they are a small shop hand-crafting electronics.

## Why this was written

First and foremost - this is a little utility I wrote on a whim. It's probably not great python code. It's probably got some innefficicies in it.

I wrote this because I was bored, the weather sucked and I got curious. I wanted to know where I was in line, how long it was going to take to get my amp made etc.

The code I have written only hits their api once a day. It is hopefully a non-issue for them. I'm sure there are people checking more frequently than that.

## Where does the data go

I have a [mongo](https://www.mongodb.com/) free tier instance backing the data. I wrote a dashboard up with some stats.

I was going to use mongo locally on a raspberry pi but the arm image produced won't run there. Ditto with the docker image. Mongo has a free tier and I'm not dealing with a lot of data so I punted and went with a free cloudy thing.

# Possible TODOs

There are a few things missing:

1. easy to consume stats
    * The stats are logged
    * The stats are also persisted to a mongo collection
        * I may write a simple web app to replace using mongodb's dashboard
1. I'm not sure what happens to an amp when they complete it
    * I'm pretty sure based on what I'm seeing - it simply does not show up anymore
    * If this is true a change in the scraper.py to find the database entries and look in the entries list and then updating status to Complete or something would suffice
1. The scraper.py code is pretty inefficient in spots
    * The db comparison takes like 3 minutes for some reason. It may be because of the free tier db and slow queries
1. The scraper.py code has a few hard-coded things
1. The scraper.py code is very lacking in using method calls for things

# Setting up your own

So, if you want to set this up for yourself there are a few things to do:

1. You need a [mongo](https://www.mongodb.com/) database
1. You need python, I wrote this against python 3.13
1. You need a [virtualenv](https://docs.python.org/3/library/venv.html)
1. You need a place to run the scraper
1. You need a config file

## The config file

Reference the [example_config.yaml](https://github.com/bilsch/decware_waitinglist/blob/main/example_config.yaml)

The only thing you should need to change about it is the `mongo_uri` value. This needs to conform to a valid pymongo / mongo uri. If you use the mongodb free tier like I did they give you a connection uri just use that. 

The value in the example config is great for local debugging / running.