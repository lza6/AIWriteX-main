//! PyO3 Vector Operations - 高性能向量计算
//! 
//! 编译方式:
//! maturin develop --release
//! 或
//! pip install maturin && maturin develop

use pyo3::prelude::*;
use std::f32;

/// 计算两个向量的余弦相似度
#[pyfunction]
pub fn cosine_similarity(a: Vec<f32>, b: Vec<f32>) -> f32 {
    if a.len() != b.len() || a.is_empty() {
        return 0.0;
    }

    let mut dot_product: f32 = 0.0;
    let mut norm_a: f32 = 0.0;
    let mut norm_b: f32 = 0.0;

    for i in 0..a.len() {
        dot_product += a[i] * b[i];
        norm_a += a[i] * a[i];
        norm_b += b[i] * b[i];
    }

    norm_a = norm_a.sqrt();
    norm_b = norm_b.sqrt();

    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }

    dot_product / (norm_a * norm_b)
}

/// 批量计算余弦相似度
#[pyfunction]
pub fn cosine_similarity_batch(query: Vec<f32>, vectors: Vec<Vec<f32>>) -> Vec<f32> {
    if query.is_empty() {
        return vectors.iter().map(|_| 0.0).collect();
    }

    let query_norm: f32 = query.iter().map(|x| x * x).sum::<f32>().sqrt();
    if query_norm == 0.0 {
        return vectors.iter().map(|_| 0.0).collect();
    }

    vectors
        .iter()
        .map(|vec| {
            if vec.len() != query.len() {
                return 0.0;
            }
            
            let dot_product: f32 = query.iter().zip(vec.iter()).map(|(a, b)| a * b).sum();
            let norm_b: f32 = vec.iter().map(|x| x * x).sum::<f32>().sqrt();
            
            if norm_b == 0.0 {
                0.0
            } else {
                dot_product / (query_norm * norm_b)
            }
        })
        .collect()
}

/// 计算欧氏距离
#[pyfunction]
pub fn euclidean_distance(a: Vec<f32>, b: Vec<f32>) -> f32 {
    if a.len() != b.len() {
        return f32::MAX;
    }

    a.iter()
        .zip(b.iter())
        .map(|(x, y)| (x - y) * (x - y))
        .sum::<f32>()
        .sqrt()
}

/// 批量计算欧氏距离
#[pyfunction]
pub fn euclidean_distance_batch(query: Vec<f32>, vectors: Vec<Vec<f32>>) -> Vec<f32> {
    vectors
        .iter()
        .map(|vec| euclidean_distance(query.clone(), vec.clone()))
        .collect()
}

/// 计算点积
#[pyfunction]
pub fn dot_product(a: Vec<f32>, b: Vec<f32>) -> f32 {
    if a.len() != b.len() {
        return 0.0;
    }

    a.iter().zip(b.iter()).map(|(a, b)| a * b).sum()
}

/// 归一化向量
#[pyfunction]
pub fn normalize(vector: Vec<f32>) -> Vec<f32> {
    let norm: f32 = vector.iter().map(|x| x * x).sum::<f32>().sqrt();
    
    if norm == 0.0 {
        return vector;
    }

    vector.iter().map(|x| x / norm).collect()
}

/// 批量归一化
#[pyfunction]
pub fn normalize_batch(vectors: Vec<Vec<f32>>) -> Vec<Vec<f32>> {
    vectors.iter().map(|v| normalize(v.clone())).collect()
}

/// Top-K 索引
#[pyfunction]
pub fn top_k_indices(scores: Vec<f32>, k: usize) -> Vec<usize> {
    let mut indexed: Vec<(usize, f32)> = scores
        .iter()
        .enumerate()
        .map(|(i, &s)| (i, s))
        .collect();

    // 部分排序，只取前 k 个
    let k = k.min(scores.len());
    indexed.select_nth_unstable_by(k, |a, b| b.1.partial_cmp(&a.1).unwrap());

    indexed[..k]
        .iter()
        .map(|(i, _)| *i)
        .collect()
}

/// 向量运算模块
#[pymodule]
pub fn _vector_ops(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(cosine_similarity, m)?)?;
    m.add_function(wrap_pyfunction!(cosine_similarity_batch, m)?)?;
    m.add_function(wrap_pyfunction!(euclidean_distance, m)?)?;
    m.add_function(wrap_pyfunction!(euclidean_distance_batch, m)?)?;
    m.add_function(wrap_pyfunction!(dot_product, m)?)?;
    m.add_function(wrap_pyfunction!(normalize, m)?)?;
    m.add_function(wrap_pyfunction!(normalize_batch, m)?)?;
    m.add_function(wrap_pyfunction!(top_k_indices, m)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_cosine_similarity() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0];
        let c = vec![0.0, 1.0, 0.0];

        assert!((cosine_similarity(a, b) - 1.0).abs() < 0.001);
        assert!(cosine_similarity(a, c).abs() < 0.001);
    }

    #[test]
    fn test_top_k() {
        let scores = vec![0.1, 0.5, 0.3, 0.9, 0.2];
        let top_k = top_k_indices(scores, 3);
        
        assert_eq!(top_k, vec![3, 1, 2]);
    }
}
