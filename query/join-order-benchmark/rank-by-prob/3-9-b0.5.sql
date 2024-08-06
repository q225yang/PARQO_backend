
    SELECT MIN(t.title) AS movie_title
    FROM keyword AS k,
        movie_info AS mi,
        movie_keyword AS mk,
        title AS t
    WHERE k.keyword = 'computer-animation'
    AND mi.info IN ('Bulgaria')
    AND t.production_year BETWEEN 2005 AND 2008
    AND t.id = mi.movie_id
    AND t.id = mk.movie_id
    AND mk.movie_id = mi.movie_id
    AND k.id = mk.keyword_id;
    