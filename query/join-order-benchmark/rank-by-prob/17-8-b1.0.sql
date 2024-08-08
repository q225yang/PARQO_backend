
        SELECT MIN(n.name) AS member_in_charnamed_american_movie,
            MIN(n.name) AS a1
        FROM cast_info AS ci,
            company_name AS cn,
            keyword AS k,
            movie_companies AS mc,
            movie_keyword AS mk,
            name AS n,
            title AS t
        WHERE cn.country_code ='[us]'
  AND cn.name = 'DreamWorks Animation'
        AND k.keyword IN ('superhero', 'marvel-comics', 'based-on-comic', 'tv-special', 'fight', 'violence', 'magnet', 'web', 'claw', 'laser')
        AND n.name LIKE '%Downey%Robert%'
        AND n.id = ci.person_id
        AND ci.movie_id = t.id
        AND t.id = mk.movie_id
        AND mk.keyword_id = k.id
        AND t.id = mc.movie_id
        AND mc.company_id = cn.id
        AND ci.movie_id = mc.movie_id
        AND ci.movie_id = mk.movie_id
        AND mc.movie_id = mk.movie_id;
        