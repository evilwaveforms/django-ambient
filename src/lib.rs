use pyo3::pymodule;

pub mod ringbuf;
pub mod sql;
pub mod store;

/// A Python module implemented in Rust. The name of this module must match
/// the `lib.name` setting in the `Cargo.toml`, else Python will not be able to
/// import the module.
#[pymodule]
mod _core {
    use crate::{sql::annotate_duplicates, store::{RequestData, Store}};
    use pyo3::prelude::*;
    use std::sync::{
        atomic::{AtomicU64, Ordering},
        Mutex, OnceLock,
    };

    const MAX_REQUESTS: usize = 100;
    static NEXT_ID: AtomicU64 = AtomicU64::new(1);
    static STORE: OnceLock<Mutex<Store>> = OnceLock::new();

    fn store() -> &'static Mutex<Store> {
        STORE.get_or_init(|| Mutex::new(Store::new(MAX_REQUESTS)))
    }

    fn new_profile_id() -> u64 {
        NEXT_ID.fetch_add(1, Ordering::Relaxed)
    }

    #[pyfunction]
    fn start_profile() -> PyResult<u64> {
        Ok(new_profile_id())
    }

    #[pyfunction]
    fn record_queries(
        request_id: u64,
        path: &str,
        method: &str,
        status: u16,
        queries: Vec<(String, u16, f64)>,
        started_at: f64,
    ) -> PyResult<Option<u64>> {
        let mut store = store()
            .lock()
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("store poisoned"))?;
        let evicted = store.insert(RequestData {
            id: request_id,
            path: path.to_string(),
            method: method.to_string(),
            status,
            queries,
            started_at,
        });
        Ok(evicted)
    }

    #[pyfunction]
    fn get_request(
        request_id: u64,
    ) -> PyResult<Option<(String, String, u16, Vec<(String, u16, f64)>, f64)>> {
        let store = store()
            .lock()
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("store poisoned"))?;
        Ok(store.get(request_id).map(|req| {
            (
                req.path.clone(),
                req.method.clone(),
                req.status,
                annotate_duplicates(&req.queries),
                req.started_at,
            )
        }))
    }

    #[pyfunction]
    fn list_requests() -> PyResult<Vec<(u64, String, String, u16, usize, f64, f64)>> {
        let store = store()
            .lock()
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("store poisoned"))?;
        Ok(store
            .iter_newest_first()
            .map(|req| {
                let count = req.queries.len();
                let total_ms: f64 = req.queries.iter().map(|q| q.2).sum();
                (
                    req.id,
                    req.path.clone(),
                    req.method.clone(),
                    req.status,
                    count,
                    total_ms,
                    req.started_at,
                )
            })
            .collect())
    }

    #[pyfunction]
    fn max_requests() -> PyResult<usize> {
        Ok(MAX_REQUESTS)
    }
}
