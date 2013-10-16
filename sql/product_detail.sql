/**
 * product_detail.sql
 *
 * COPY product name, detail_url to tsv file
 *
 * Usage: Takes a single parameter (outfile) which is the path to the 
 * write the tsv data to.
 *
 *     psql star < product_detail.sql -v outfile=/path/to/data.tsv
 *
 */
 
-------------------------------------------------------------------------
-- Ensure transaction security by placing all CREATE and ALTER statements
-- inside of `BEGIN` and `COMMIT` statements.
-------------------------------------------------------------------------
 
BEGIN;
 
COPY (SELECT product, url FROM (
        SELECT merchant.name AS merchant, product.name AS product, COALESCE(sku.detail_url, sku.buy_url, NULL) AS url
                from sku
		        join product on product.id = sku.product_id
		        join merchant on merchant.id = sku.merchant_id) AS prods
      WHERE url IS NOT NULL) 
    TO :'infile'
    WITH ENCODING 'utf8';
 
COMMIT;
 
-------------------------------------------------------------------------
-- No CREATE or ALTER statements should be outside of the `COMMIT`.
-------------------------------------------------------------------------
