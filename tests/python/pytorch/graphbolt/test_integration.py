import dgl
import dgl.graphbolt as gb
import dgl.sparse as dglsp
import torch


def test_integration_link_prediction():
    torch.manual_seed(926)

    indptr = torch.tensor([0, 0, 1, 3, 6, 8, 10])
    indices = torch.tensor([5, 3, 3, 3, 3, 4, 4, 0, 5, 4])

    matrix_a = dglsp.from_csc(indptr, indices)
    node_pairs = torch.t(torch.stack(matrix_a.coo()))
    node_feature_data = torch.tensor(
        [
            [0.9634, 0.2294],
            [0.6172, 0.7865],
            [0.2109, 0.1089],
            [0.8672, 0.2276],
            [0.5503, 0.8223],
            [0.5160, 0.2486],
        ]
    )
    edge_feature_data = torch.tensor(
        [
            [0.5123, 0.1709, 0.6150],
            [0.1476, 0.1902, 0.1314],
            [0.2582, 0.5203, 0.6228],
            [0.3708, 0.7631, 0.2683],
            [0.2126, 0.7878, 0.7225],
            [0.7885, 0.3414, 0.5485],
            [0.4088, 0.8200, 0.1851],
            [0.0056, 0.9469, 0.4432],
            [0.8972, 0.7511, 0.3617],
            [0.5773, 0.2199, 0.3366],
        ]
    )

    item_set = gb.ItemSet(node_pairs, names="node_pairs")
    graph = gb.fused_csc_sampling_graph(indptr, indices)

    node_feature = gb.TorchBasedFeature(node_feature_data)
    edge_feature = gb.TorchBasedFeature(edge_feature_data)
    features = {
        ("node", None, "feat"): node_feature,
        ("edge", None, "feat"): edge_feature,
    }
    feature_store = gb.BasicFeatureStore(features)
    datapipe = gb.ItemSampler(item_set, batch_size=4)
    datapipe = datapipe.sample_uniform_negative(graph, 1)
    fanouts = torch.LongTensor([1])
    datapipe = datapipe.sample_neighbor(graph, [fanouts, fanouts], replace=True)
    datapipe = datapipe.transform(gb.exclude_seed_edges)
    datapipe = datapipe.fetch_feature(
        feature_store, node_feature_keys=["feat"], edge_feature_keys=["feat"]
    )
    dataloader = gb.DataLoader(
        datapipe,
    )
    expected = [
        str(
            """MiniBatch(seed_nodes=None,
          sampled_subgraphs=[SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 1, 1, 1, 1, 1, 2]),
                                                                         indices=tensor([5, 4]),
                                                           ),
                                               original_row_node_ids=tensor([5, 3, 1, 2, 0, 4]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([5, 3, 1, 2, 0, 4]),
                            ),
                            SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 1, 1, 1, 1, 1]),
                                                                         indices=tensor([5]),
                                                           ),
                                               original_row_node_ids=tensor([5, 3, 1, 2, 0, 4]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([5, 3, 1, 2, 0]),
                            )],
          positive_node_pairs=(tensor([0, 1, 1, 1]),
                              tensor([2, 3, 3, 1])),
          node_pairs_with_labels=((tensor([0, 1, 1, 1, 0, 1, 1, 1]), tensor([2, 3, 3, 1, 4, 4, 1, 4])),
                                 tensor([1., 1., 1., 1., 0., 0., 0., 0.])),
          node_pairs=(tensor([5, 3, 3, 3]),
                     tensor([1, 2, 2, 3])),
          node_features={'feat': tensor([[0.5160, 0.2486],
                                [0.8672, 0.2276],
                                [0.6172, 0.7865],
                                [0.2109, 0.1089],
                                [0.9634, 0.2294],
                                [0.5503, 0.8223]])},
          negative_srcs=tensor([[5],
                                [3],
                                [3],
                                [3]]),
          negative_node_pairs=(tensor([0, 1, 1, 1]),
                              tensor([4, 4, 1, 4])),
          negative_dsts=tensor([[0],
                                [0],
                                [3],
                                [0]]),
          labels=None,
          input_nodes=tensor([5, 3, 1, 2, 0, 4]),
          edge_features=[{},
                        {}],
          compacted_node_pairs=(tensor([0, 1, 1, 1]),
                               tensor([2, 3, 3, 1])),
          compacted_negative_srcs=tensor([[0],
                                          [1],
                                          [1],
                                          [1]]),
          compacted_negative_dsts=tensor([[4],
                                          [4],
                                          [1],
                                          [4]]),
          blocks=[Block(num_src_nodes=6, num_dst_nodes=6, num_edges=2),
                 Block(num_src_nodes=6, num_dst_nodes=5, num_edges=1)],
       )"""
        ),
        str(
            """MiniBatch(seed_nodes=None,
          sampled_subgraphs=[SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 0, 0, 0, 1, 2]),
                                                                         indices=tensor([1, 3]),
                                                           ),
                                               original_row_node_ids=tensor([3, 4, 0, 5, 1]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([3, 4, 0, 5, 1]),
                            ),
                            SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 0, 0, 0, 1, 2]),
                                                                         indices=tensor([1, 3]),
                                                           ),
                                               original_row_node_ids=tensor([3, 4, 0, 5, 1]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([3, 4, 0, 5, 1]),
                            )],
          positive_node_pairs=(tensor([0, 1, 1, 2]),
                              tensor([0, 0, 1, 1])),
          node_pairs_with_labels=((tensor([0, 1, 1, 2, 0, 1, 1, 2]), tensor([0, 0, 1, 1, 1, 1, 3, 4])),
                                 tensor([1., 1., 1., 1., 0., 0., 0., 0.])),
          node_pairs=(tensor([3, 4, 4, 0]),
                     tensor([3, 3, 4, 4])),
          node_features={'feat': tensor([[0.8672, 0.2276],
                                [0.5503, 0.8223],
                                [0.9634, 0.2294],
                                [0.5160, 0.2486],
                                [0.6172, 0.7865]])},
          negative_srcs=tensor([[3],
                                [4],
                                [4],
                                [0]]),
          negative_node_pairs=(tensor([0, 1, 1, 2]),
                              tensor([1, 1, 3, 4])),
          negative_dsts=tensor([[4],
                                [4],
                                [5],
                                [1]]),
          labels=None,
          input_nodes=tensor([3, 4, 0, 5, 1]),
          edge_features=[{},
                        {}],
          compacted_node_pairs=(tensor([0, 1, 1, 2]),
                               tensor([0, 0, 1, 1])),
          compacted_negative_srcs=tensor([[0],
                                          [1],
                                          [1],
                                          [2]]),
          compacted_negative_dsts=tensor([[1],
                                          [1],
                                          [3],
                                          [4]]),
          blocks=[Block(num_src_nodes=5, num_dst_nodes=5, num_edges=2),
                 Block(num_src_nodes=5, num_dst_nodes=5, num_edges=2)],
       )"""
        ),
        str(
            """MiniBatch(seed_nodes=None,
          sampled_subgraphs=[SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 0, 1]),
                                                                         indices=tensor([1]),
                                                           ),
                                               original_row_node_ids=tensor([5, 4]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([5, 4]),
                            ),
                            SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 0, 1]),
                                                                         indices=tensor([1]),
                                                           ),
                                               original_row_node_ids=tensor([5, 4]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([5, 4]),
                            )],
          positive_node_pairs=(tensor([0, 1]),
                              tensor([0, 0])),
          node_pairs_with_labels=((tensor([0, 1, 0, 1]), tensor([0, 0, 0, 0])),
                                 tensor([1., 1., 0., 0.])),
          node_pairs=(tensor([5, 4]),
                     tensor([5, 5])),
          node_features={'feat': tensor([[0.5160, 0.2486],
                                [0.5503, 0.8223]])},
          negative_srcs=tensor([[5],
                                [4]]),
          negative_node_pairs=(tensor([0, 1]),
                              tensor([0, 0])),
          negative_dsts=tensor([[5],
                                [5]]),
          labels=None,
          input_nodes=tensor([5, 4]),
          edge_features=[{},
                        {}],
          compacted_node_pairs=(tensor([0, 1]),
                               tensor([0, 0])),
          compacted_negative_srcs=tensor([[0],
                                          [1]]),
          compacted_negative_dsts=tensor([[0],
                                          [0]]),
          blocks=[Block(num_src_nodes=2, num_dst_nodes=2, num_edges=1),
                 Block(num_src_nodes=2, num_dst_nodes=2, num_edges=1)],
       )"""
        ),
    ]
    for step, data in enumerate(dataloader):
        assert expected[step] == str(data), print(data)


def test_integration_node_classification():
    torch.manual_seed(926)

    indptr = torch.tensor([0, 0, 1, 3, 6, 8, 10])
    indices = torch.tensor([5, 3, 3, 3, 3, 4, 4, 0, 5, 4])

    matrix_a = dglsp.from_csc(indptr, indices)
    node_pairs = torch.t(torch.stack(matrix_a.coo()))
    node_feature_data = torch.tensor(
        [
            [0.9634, 0.2294],
            [0.6172, 0.7865],
            [0.2109, 0.1089],
            [0.8672, 0.2276],
            [0.5503, 0.8223],
            [0.5160, 0.2486],
        ]
    )
    edge_feature_data = torch.tensor(
        [
            [0.5123, 0.1709, 0.6150],
            [0.1476, 0.1902, 0.1314],
            [0.2582, 0.5203, 0.6228],
            [0.3708, 0.7631, 0.2683],
            [0.2126, 0.7878, 0.7225],
            [0.7885, 0.3414, 0.5485],
            [0.4088, 0.8200, 0.1851],
            [0.0056, 0.9469, 0.4432],
            [0.8972, 0.7511, 0.3617],
            [0.5773, 0.2199, 0.3366],
        ]
    )

    item_set = gb.ItemSet(node_pairs, names="node_pairs")
    graph = gb.fused_csc_sampling_graph(indptr, indices)

    node_feature = gb.TorchBasedFeature(node_feature_data)
    edge_feature = gb.TorchBasedFeature(edge_feature_data)
    features = {
        ("node", None, "feat"): node_feature,
        ("edge", None, "feat"): edge_feature,
    }
    feature_store = gb.BasicFeatureStore(features)
    datapipe = gb.ItemSampler(item_set, batch_size=4)
    fanouts = torch.LongTensor([1])
    datapipe = datapipe.sample_neighbor(graph, [fanouts, fanouts], replace=True)
    datapipe = datapipe.fetch_feature(
        feature_store, node_feature_keys=["feat"], edge_feature_keys=["feat"]
    )
    dataloader = gb.DataLoader(
        datapipe,
    )
    expected = [
        str(
            """MiniBatch(seed_nodes=None,
          sampled_subgraphs=[SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 1, 2, 3, 4]),
                                                                         indices=tensor([4, 1, 0, 1]),
                                                           ),
                                               original_row_node_ids=tensor([5, 3, 1, 2, 4]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([5, 3, 1, 2]),
                            ),
                            SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 1, 2, 3, 4]),
                                                                         indices=tensor([0, 1, 0, 1]),
                                                           ),
                                               original_row_node_ids=tensor([5, 3, 1, 2]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([5, 3, 1, 2]),
                            )],
          positive_node_pairs=(tensor([0, 1, 1, 1]),
                              tensor([2, 3, 3, 1])),
          node_pairs_with_labels=None,
          node_pairs=(tensor([5, 3, 3, 3]),
                     tensor([1, 2, 2, 3])),
          node_features={'feat': tensor([[0.5160, 0.2486],
                                [0.8672, 0.2276],
                                [0.6172, 0.7865],
                                [0.2109, 0.1089],
                                [0.5503, 0.8223]])},
          negative_srcs=None,
          negative_node_pairs=None,
          negative_dsts=None,
          labels=None,
          input_nodes=tensor([5, 3, 1, 2, 4]),
          edge_features=[{},
                        {}],
          compacted_node_pairs=(tensor([0, 1, 1, 1]),
                               tensor([2, 3, 3, 1])),
          compacted_negative_srcs=None,
          compacted_negative_dsts=None,
          blocks=[Block(num_src_nodes=5, num_dst_nodes=4, num_edges=4),
                 Block(num_src_nodes=4, num_dst_nodes=4, num_edges=4)],
       )"""
        ),
        str(
            """MiniBatch(seed_nodes=None,
          sampled_subgraphs=[SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 1, 2, 2]),
                                                                         indices=tensor([0, 2]),
                                                           ),
                                               original_row_node_ids=tensor([3, 4, 0]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([3, 4, 0]),
                            ),
                            SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 1, 2, 2]),
                                                                         indices=tensor([0, 2]),
                                                           ),
                                               original_row_node_ids=tensor([3, 4, 0]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([3, 4, 0]),
                            )],
          positive_node_pairs=(tensor([0, 1, 1, 2]),
                              tensor([0, 0, 1, 1])),
          node_pairs_with_labels=None,
          node_pairs=(tensor([3, 4, 4, 0]),
                     tensor([3, 3, 4, 4])),
          node_features={'feat': tensor([[0.8672, 0.2276],
                                [0.5503, 0.8223],
                                [0.9634, 0.2294]])},
          negative_srcs=None,
          negative_node_pairs=None,
          negative_dsts=None,
          labels=None,
          input_nodes=tensor([3, 4, 0]),
          edge_features=[{},
                        {}],
          compacted_node_pairs=(tensor([0, 1, 1, 2]),
                               tensor([0, 0, 1, 1])),
          compacted_negative_srcs=None,
          compacted_negative_dsts=None,
          blocks=[Block(num_src_nodes=3, num_dst_nodes=3, num_edges=2),
                 Block(num_src_nodes=3, num_dst_nodes=3, num_edges=2)],
       )"""
        ),
        str(
            """MiniBatch(seed_nodes=None,
          sampled_subgraphs=[SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 1, 2]),
                                                                         indices=tensor([0, 2]),
                                                           ),
                                               original_row_node_ids=tensor([5, 4, 0]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([5, 4]),
                            ),
                            SampledSubgraphImpl(sampled_csc=CSCFormatBase(indptr=tensor([0, 1, 2]),
                                                                         indices=tensor([1, 1]),
                                                           ),
                                               original_row_node_ids=tensor([5, 4]),
                                               original_edge_ids=None,
                                               original_column_node_ids=tensor([5, 4]),
                            )],
          positive_node_pairs=(tensor([0, 1]),
                              tensor([0, 0])),
          node_pairs_with_labels=None,
          node_pairs=(tensor([5, 4]),
                     tensor([5, 5])),
          node_features={'feat': tensor([[0.5160, 0.2486],
                                [0.5503, 0.8223],
                                [0.9634, 0.2294]])},
          negative_srcs=None,
          negative_node_pairs=None,
          negative_dsts=None,
          labels=None,
          input_nodes=tensor([5, 4, 0]),
          edge_features=[{},
                        {}],
          compacted_node_pairs=(tensor([0, 1]),
                               tensor([0, 0])),
          compacted_negative_srcs=None,
          compacted_negative_dsts=None,
          blocks=[Block(num_src_nodes=3, num_dst_nodes=2, num_edges=2),
                 Block(num_src_nodes=2, num_dst_nodes=2, num_edges=2)],
       )"""
        ),
    ]
    for step, data in enumerate(dataloader):
        assert expected[step] == str(data), print(data)
