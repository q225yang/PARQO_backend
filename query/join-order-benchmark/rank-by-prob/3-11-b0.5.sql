
    SELECT MIN(t.title) AS movie_title
    FROM keyword AS k,
        movie_info AS mi,
        movie_keyword AS mk,
        title AS t
    WHERE k.keyword IS NOT NULL AND k.keyword IN ('murder', 'murder-in-title', 'blood', 'violence')
    AND mi.info IN ('Drama', 'Horror')
    AND t.production_year = 1998 AND t.title LIKE '%Money%'
    AND t.id = mi.movie_id
    AND t.id = mk.movie_id
    AND mk.movie_id = mi.movie_id
    AND k.id = mk.keyword_id;
    