from queue import Queue


# keeps track of the newest self.length (key, value) pairs
# backed by hashmap so elements in the queue are guaranteed to be unique
# wrote this to keep track of the newest X number of reddit posts returned by a search
# same functionality can be achieved with just a hashmap, but that grows larger and larger over time
# so keep track of only self.length pairs

class SlidingWindowMap(object):

    def __init__(self, length):
        self.map = {}
        self.q = Queue()
        self.length = length

    def put(self, key, value):
        if key not in self.map:
            # remove the oldest element if the queue reaches max size
            if self.q.qsize() == self.length:
                del self.map[self.q.get()]
            # put the new post in
            self.q.put(key)
            self.map[key] = value
            return True

        return False

    def get(self, key):
        return self.map[key]
