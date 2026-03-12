use crate::ringbuf::RingBuf;
use std::collections::HashMap;

pub struct RequestData {
    pub id: u64,
    pub path: String,
    pub method: String,
    pub status: u16,
    pub queries: Vec<(String, u16, f64)>,
    pub started_at: f64,
}

pub struct Store {
    ring: RingBuf<RequestData>,
    index: HashMap<u64, usize>,
}

impl Store {
    pub fn new(cap: usize) -> Self {
        Self {
            ring: RingBuf::new(cap),
            index: HashMap::with_capacity(cap),
        }
    }

    pub fn insert(&mut self, req: RequestData) -> Option<u64> {
        let cap = self.ring.capacity();
        if cap == 0 {
            return None;
        }
        let id = req.id;
        let (idx, evicted) = self.ring.push_with_index(req);
        let evicted_id = if let Some(old) = evicted {
            self.index.remove(&old.id);
            Some(old.id)
        } else {
            None
        };
        self.index.insert(id, idx);
        evicted_id
    }

    pub fn get(&self, id: u64) -> Option<&RequestData> {
        self.index.get(&id).and_then(|&i| self.ring.get(i))
    }

    pub fn iter(&self) -> impl Iterator<Item = &RequestData> {
        self.ring.iter()
    }

    pub fn iter_newest_first(&self) -> impl Iterator<Item = &RequestData> {
        self.ring.iter_newest_first()
    }
}
