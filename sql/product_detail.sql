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
        SELECT vendor.name AS vendor, product.name AS product, COALESCE(shelf.detail_url, shelf.buy_url, NULL) AS url
                from shelf
		        join product on product.id = shelf.product_id
		        join vendor on vendor.id = shelf.vendor_id) AS prods
      WHERE url IS NOT NULL) 
    TO :'infile'
    WITH ENCODING 'utf8';
 
COMMIT;
 
-------------------------------------------------------------------------
-- No CREATE or ALTER statements should be outside of the `COMMIT`.
-------------------------------------------------------------------------
