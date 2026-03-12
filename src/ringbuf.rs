pub struct RingBuf<T> {
    buf: Vec<Option<T>>,
    /// Index of oldest
    head: usize,
    len: usize,
}

impl<T> RingBuf<T> {
    pub fn new(cap: usize) -> Self {
        let mut buf = Vec::with_capacity(cap);
        buf.resize_with(cap, || None);
        Self {
            buf,
            head: 0,
            len: 0,
        }
    }

    #[inline]
    pub fn capacity(&self) -> usize {
        self.buf.len()
    }

    #[inline]
    pub fn push(&mut self, value: T) -> Option<T> {
        let cap = self.capacity();
        if cap == 0 {
            return Some(value);
        }
        let tail = (self.head + self.len) % cap;
        let evicted = self.buf[tail].take();
        self.buf[tail] = Some(value);
        if self.len < cap {
            self.len += 1;
        } else {
            self.head = (self.head + 1) % cap;
        }
        evicted
    }

    #[inline]
    pub fn push_with_index(&mut self, value: T) -> (usize, Option<T>) {
        let cap = self.capacity();
        if cap == 0 {
            return (0, Some(value));
        }
        let tail = (self.head + self.len) % cap;
        let evicted = self.buf[tail].take();
        self.buf[tail] = Some(value);
        if self.len < cap {
            self.len += 1;
        } else {
            self.head = (self.head + 1) % cap;
        }
        (tail, evicted)
    }

    #[inline]
    pub fn len(&self) -> usize {
        self.len
    }

    #[inline]
    pub fn is_empty(&self) -> bool {
        self.len == 0
    }

    #[inline]
    pub fn head_index(&self) -> usize {
        self.head
    }

    #[inline]
    pub fn get(&self, i: usize) -> Option<&T> {
        if i >= self.len {
            return None;
        }
        let cap = self.capacity();
        if cap == 0 {
            return None;
        }
        let idx = (self.head + i) % cap;
        self.buf[idx].as_ref()
    }

    pub fn iter(&self) -> impl Iterator<Item = &T> {
        let cap = self.capacity();
        (0..self.len).filter_map(move |i| {
            let idx = (self.head + i) % cap;
            self.buf[idx].as_ref()
        })
    }

    pub fn iter_newest_first(&self) -> impl Iterator<Item = &T> {
        let cap = self.capacity();
        (0..self.len).filter_map(move |i| {
            if cap == 0 {
                return None;
            }
            let idx = (self.head + self.len - 1 - i) % cap;
            self.buf[idx].as_ref()
        })
    }
}
