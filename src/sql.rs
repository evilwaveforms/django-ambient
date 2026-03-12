use std::collections::HashMap;

pub fn annotate_duplicates(data: &[(String, u16, f64)]) -> Vec<(String, u16, f64)> {
    let mut counts: HashMap<&str, u16> = HashMap::new();
    for (query, _, _) in data {
        let entry = counts.entry(query.as_str()).or_insert(0);
        *entry = entry.saturating_add(1);
    }
    data.iter()
        .map(|(query, _, duration_ms)| {
            let count = counts.get(query.as_str()).copied().unwrap_or(0);
            (query.clone(), count, *duration_ms)
        })
        .collect()
}
