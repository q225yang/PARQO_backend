
    SELECT MIN(t.title) AS movie_title
    FROM keyword AS k,
        movie_info AS mi,
        movie_keyword AS mk,
        title AS t
    WHERE k.keyword IN ('superhero', 'marvel-comics', 'based-on-comic', 'fight')
    AND mi.info IN ('Sweden', 'Germany', 'Swedish', 'German')
    AND t.title = 'Shrek 2'
  AND t.production_year BETWEEN 2000 AND 2005
    AND t.id = mi.movie_id
    AND t.id = mk.movie_id
    AND mk.movie_id = mi.movie_id
    AND k.id = mk.keyword_id;
    