from queue import Queue


# keeps track of the newest self.length key, value pairs
# backed by hashmap so elements in the queue are guaranteed to be unique
# wrote this to keep track of the newest X number of reddit posts returned by a search

class SlidingWindowMap(object):

    def __init__(self, length):
        self.map = {}
        self.q = Queue()
        self.length = length

    def __iter__(self):
        return self.map.__iter__()

    def __next__(self):
        return self.map

    def put(self, key, value):
        if key not in self.map:
            # remove the first element if the queue reaches max size
            if self.q.qsize() == self.length:
                del self.map[self.q.get()]
            self.q.put(key)
            self.map[key] = value
            return True

        return False

    def get(self, key):
        return self.map[key]
