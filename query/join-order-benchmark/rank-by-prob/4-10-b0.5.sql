
    SELECT MIN(mi_idx.info) AS rating,
       MIN(t.title) AS movie_title
    FROM info_type AS it,
        keyword AS k,
        movie_info_idx AS mi_idx,
        movie_keyword AS mk,
        title AS t
    WHERE it.info = 'rating'
    AND k.keyword = 'marvel-cinematic-universe'
    AND mi_idx.info < '8.5'
    AND t.production_year > 2010
  AND t.title LIKE 'Vampire%'
    AND t.id = mi_idx.movie_id
    AND t.id = mk.movie_id
    AND mk.movie_id = mi_idx.movie_id
    AND k.id = mk.keyword_id
    AND it.id = mi_idx.info_type_id;
    