# Collection of interesting things

## Count of entries by day

This is formatted for mongo cli. Adapting to python should be pretty easy

```
db.entries.aggregate([
    {
        '$project': {
            count: {'$dateToString': {format: '%Y-%m-%d', date: '$date'}}
        }
    }, {
        '$group': {
            _id: {count: '$count'},
            viewCount: {'$sum': 1}
        }
    },
    {'$sort': {'_id.count': 1}}
])
```