/**
 *  Copyright (c) 2023 by Contributors
 *  Copyright (c) 2023, GT-TDAlab (Muhammed Fatih Balin & Umit V. Catalyurek)
 * @file cuda/sampling_utils.cu
 * @brief Sampling utility function implementations on CUDA.
 */
#include <thrust/execution_policy.h>
#include <thrust/iterator/counting_iterator.h>

#include <cub/cub.cuh>

#include "./common.h"
#include "./utils.h"

namespace graphbolt {
namespace ops {

// Given rows and indptr, computes:
// inrow_indptr[i] = indptr[rows[i]];
// in_degree[i] = indptr[rows[i] + 1] - indptr[rows[i]];
template <typename indptr_t, typename nodes_t>
struct SliceFunc {
  const nodes_t* rows;
  const indptr_t* indptr;
  indptr_t* in_degree;
  indptr_t* inrow_indptr;
  __host__ __device__ auto operator()(int64_t tIdx) {
    const auto out_row = rows[tIdx];
    const auto indptr_val = indptr[out_row];
    const auto degree = indptr[out_row + 1] - indptr_val;
    in_degree[tIdx] = degree;
    inrow_indptr[tIdx] = indptr_val;
  }
};

// Returns (indptr[nodes + 1] - indptr[nodes], indptr[nodes])
std::tuple<torch::Tensor, torch::Tensor> SliceCSCIndptr(
    torch::Tensor indptr, torch::Tensor nodes) {
  auto allocator = cuda::GetAllocator();
  const auto exec_policy =
      thrust::cuda::par_nosync(allocator).on(cuda::GetCurrentStream());
  const int64_t num_nodes = nodes.size(0);
  // Read indptr only once in case it is pinned and access is slow.
  auto sliced_indptr =
      torch::empty(num_nodes, nodes.options().dtype(indptr.scalar_type()));
  // compute in-degrees
  auto in_degree =
      torch::empty(num_nodes + 1, nodes.options().dtype(indptr.scalar_type()));
  thrust::counting_iterator<int64_t> iota(0);
  AT_DISPATCH_INTEGRAL_TYPES(
      indptr.scalar_type(), "IndexSelectCSCIndptr", ([&] {
        using indptr_t = scalar_t;
        AT_DISPATCH_INDEX_TYPES(
            nodes.scalar_type(), "IndexSelectCSCNodes", ([&] {
              using nodes_t = index_t;
              thrust::for_each(
                  exec_policy, iota, iota + num_nodes,
                  SliceFunc<indptr_t, nodes_t>{
                      nodes.data_ptr<nodes_t>(), indptr.data_ptr<indptr_t>(),
                      in_degree.data_ptr<indptr_t>(),
                      sliced_indptr.data_ptr<indptr_t>()});
            }));
      }));
  return {in_degree, sliced_indptr};
}

template <typename indptr_t, typename etype_t>
struct EdgeTypeSearch {
  const indptr_t* sub_indptr;
  const indptr_t* sliced_indptr;
  const etype_t* etypes;
  int64_t num_fanouts;
  int64_t num_rows;
  indptr_t* new_sub_indptr;
  indptr_t* new_sliced_indptr;
  __host__ __device__ auto operator()(int64_t i) {
    const auto homo_i = i / num_fanouts;
    const auto indptr_i = sub_indptr[homo_i];
    const auto degree = sub_indptr[homo_i + 1] - indptr_i;
    const etype_t etype = i % num_fanouts;
    auto offset = cuda::LowerBound(etypes + indptr_i, degree, etype);
    new_sub_indptr[i] = indptr_i + offset;
    new_sliced_indptr[i] = sliced_indptr[homo_i] + offset;
    if (i == num_rows - 1) new_sub_indptr[num_rows] = indptr_i + degree;
  }
};

std::tuple<torch::Tensor, torch::Tensor, torch::Tensor> SliceCSCIndptrHetero(
    torch::Tensor sub_indptr, torch::Tensor etypes, torch::Tensor sliced_indptr,
    int64_t num_fanouts) {
  auto num_rows = (sub_indptr.size(0) - 1) * num_fanouts;
  auto new_sub_indptr = torch::empty(num_rows + 1, sub_indptr.options());
  auto new_indegree = torch::empty(num_rows + 2, sub_indptr.options());
  auto new_sliced_indptr = torch::empty(num_rows, sliced_indptr.options());
  auto allocator = cuda::GetAllocator();
  auto stream = cuda::GetCurrentStream();
  const auto exec_policy = thrust::cuda::par_nosync(allocator).on(stream);
  thrust::counting_iterator<int64_t> iota(0);
  AT_DISPATCH_INTEGRAL_TYPES(
      sub_indptr.scalar_type(), "SliceCSCIndptrHeteroIndptr", ([&] {
        using indptr_t = scalar_t;
        AT_DISPATCH_INTEGRAL_TYPES(
            etypes.scalar_type(), "SliceCSCIndptrHeteroTypePerEdge", ([&] {
              using etype_t = scalar_t;
              thrust::for_each(
                  exec_policy, iota, iota + num_rows,
                  EdgeTypeSearch<indptr_t, etype_t>{
                      sub_indptr.data_ptr<indptr_t>(),
                      sliced_indptr.data_ptr<indptr_t>(),
                      etypes.data_ptr<etype_t>(), num_fanouts, num_rows,
                      new_sub_indptr.data_ptr<indptr_t>(),
                      new_sliced_indptr.data_ptr<indptr_t>()});
            }));
        size_t tmp_storage_size = 0;
        cub::DeviceAdjacentDifference::SubtractLeftCopy(
            nullptr, tmp_storage_size, new_sub_indptr.data_ptr<indptr_t>(),
            new_indegree.data_ptr<indptr_t>(), num_rows + 1, cub::Difference{},
            stream);
        auto tmp_storage = allocator.AllocateStorage<char>(tmp_storage_size);
        cub::DeviceAdjacentDifference::SubtractLeftCopy(
            tmp_storage.get(), tmp_storage_size,
            new_sub_indptr.data_ptr<indptr_t>(),
            new_indegree.data_ptr<indptr_t>(), num_rows + 1, cub::Difference{},
            stream);
      }));
  // Discard the first element of the SubtractLeftCopy result and ensure that
  // new_indegree tensor has size num_rows + 1 so that its ExclusiveCumSum is
  // directly equivalent to new_sub_indptr.
  // Equivalent to new_indegree = new_indegree[1:] in Python.
  new_indegree = new_indegree.slice(0, 1);
  return {new_sub_indptr, new_indegree, new_sliced_indptr};
}

}  //  namespace ops
}  //  namespace graphbolt
