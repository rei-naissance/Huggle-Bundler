--
-- PostgreSQL database dump
--

\restrict xUvLH6ec8qzWe0u9pkY32mcmKMduVipqYjbeGDzg1MSHhKvr3nm9AhIzf0LIDJn

-- Dumped from database version 17.5 (84bec44)
-- Dumped by pg_dump version 17.6 (Ubuntu 17.6-1.pgdg24.04+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: postgis; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public;


--
-- Name: EXTENSION postgis; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION postgis IS 'PostGIS geometry and geography spatial types and functions';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: __EFMigrationsHistory; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public."__EFMigrationsHistory" (
    "MigrationId" character varying(150) NOT NULL,
    "ProductVersion" character varying(32) NOT NULL
);


ALTER TABLE public."__EFMigrationsHistory" OWNER TO neondb_owner;

--
-- Name: analytics; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.analytics (
    id text NOT NULL,
    "storeId" text,
    "productId" text,
    "viewCount" integer NOT NULL,
    "purchaseCount" integer NOT NULL,
    "totalRevenue" numeric(12,2) NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.analytics OWNER TO neondb_owner;

--
-- Name: buyers; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.buyers (
    id character varying(255) NOT NULL
);


ALTER TABLE public.buyers OWNER TO neondb_owner;

--
-- Name: carts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.carts (
    id text NOT NULL,
    "buyerId" character varying(255) NOT NULL,
    items jsonb,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.carts OWNER TO neondb_owner;

--
-- Name: chats; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.chats (
    id text NOT NULL,
    "buyerId" character varying(255) NOT NULL,
    "sellerId" character varying(255) NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.chats OWNER TO neondb_owner;

--
-- Name: followedstores; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.followedstores (
    "buyerId" character varying(255) NOT NULL,
    "storeId" text NOT NULL,
    "createdAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.followedstores OWNER TO neondb_owner;

--
-- Name: likedposts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.likedposts (
    "buyerId" character varying(255) NOT NULL,
    "postId" text NOT NULL,
    "createdAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.likedposts OWNER TO neondb_owner;

--
-- Name: locations; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.locations (
    id text NOT NULL,
    "BuyerId" character varying(255),
    "Latitude" double precision NOT NULL,
    "Longitude" double precision NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL,
    "Address" character varying(500),
    "City" character varying(100),
    "Coordinates" public.geography(Point,4326),
    "Label" character varying(50),
    "PostalCode" character varying(20),
    "Province" character varying(100),
    "StoreId" text
);


ALTER TABLE public.locations OWNER TO neondb_owner;

--
-- Name: messages; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.messages (
    id text NOT NULL,
    "chatId" text NOT NULL,
    "senderId" character varying(255) NOT NULL,
    "messageText" text,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.messages OWNER TO neondb_owner;

--
-- Name: notifications; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.notifications (
    id text NOT NULL,
    "userId" character varying(255) NOT NULL,
    title character varying(255),
    message text,
    type character varying(100),
    "isRead" boolean NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.notifications OWNER TO neondb_owner;

--
-- Name: orderitems; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.orderitems (
    id text NOT NULL,
    "orderId" text NOT NULL,
    "productId" text NOT NULL,
    quantity integer NOT NULL,
    "unitPrice" numeric(10,2) NOT NULL,
    "totalPrice" numeric(10,2) NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.orderitems OWNER TO neondb_owner;

--
-- Name: orders; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.orders (
    id text NOT NULL,
    "buyerId" character varying(255) NOT NULL,
    "storeId" text NOT NULL,
    "totalAmount" numeric(12,2) NOT NULL,
    notes text,
    status character varying(50) NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL,
    "deletedOn" timestamp with time zone
);


ALTER TABLE public.orders OWNER TO neondb_owner;

--
-- Name: posts; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.posts (
    id text NOT NULL,
    "storeId" text NOT NULL,
    "sellerId" character varying(255) NOT NULL,
    content text,
    "imageUrls" text NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL,
    "deletedOn" timestamp with time zone
);


ALTER TABLE public.posts OWNER TO neondb_owner;

--
-- Name: products; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.products (
    id text NOT NULL,
    "storeId" text NOT NULL,
    name character varying(255) NOT NULL,
    description text,
    image text DEFAULT ''::text NOT NULL,
    "productType" character varying(100),
    price numeric(10,2) NOT NULL,
    stock integer NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL,
    "deletedOn" timestamp with time zone,
    "expiresOn" timestamp with time zone DEFAULT '-infinity'::timestamp with time zone NOT NULL,
    "isActive" boolean DEFAULT false NOT NULL,
    "originalPrice" numeric(10,2) DEFAULT 0.0 NOT NULL,
    "productCost" numeric(10,2) DEFAULT 0.0 NOT NULL,
    tags text DEFAULT ''::text NOT NULL,
    "dynamicPricingStartDays" integer DEFAULT 14 NOT NULL,
    "isDynamicPricingEnabled" boolean DEFAULT false NOT NULL,
    "lastPriceUpdate" timestamp with time zone,
    "startingPrice" numeric(10,2) DEFAULT 0.0 NOT NULL
);


ALTER TABLE public.products OWNER TO neondb_owner;

--
-- Name: pushtokens; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.pushtokens (
    id text NOT NULL,
    "userId" character varying(255),
    token character varying(500) NOT NULL,
    "isActive" boolean NOT NULL,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.pushtokens OWNER TO neondb_owner;

--
-- Name: reports; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.reports (
    id text NOT NULL,
    "reporterId" character varying(255) NOT NULL,
    "reportedStoreId" text,
    "reportedProductId" text,
    "reportedPostId" text,
    reason character varying(255),
    description text,
    status character varying(50) NOT NULL,
    "Buyerid" character varying(255),
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.reports OWNER TO neondb_owner;

--
-- Name: reviews; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.reviews (
    id text NOT NULL,
    "buyerId" character varying(255) NOT NULL,
    "productId" text,
    "orderId" text,
    rating integer NOT NULL,
    content text,
    "imageUrl" character varying(500),
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.reviews OWNER TO neondb_owner;

--
-- Name: sellers; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.sellers (
    id character varying(255) NOT NULL,
    "phoneNumber" character varying(20),
    "isBanned" boolean NOT NULL,
    "banReason" text
);


ALTER TABLE public.sellers OWNER TO neondb_owner;

--
-- Name: stores; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.stores (
    id text NOT NULL,
    "sellerId" character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    "storeType" character varying(100),
    description text,
    "phoneNumber" character varying(20),
    "profileImageUrl" character varying(500),
    address text,
    city character varying(100),
    province character varying(100),
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL,
    "deletedOn" timestamp with time zone,
    "LocationId" text,
    "businessHours" text DEFAULT ''::text NOT NULL,
    "coverImageUrl" character varying(500),
    "isOpen" boolean DEFAULT false NOT NULL,
    "isVerified" boolean DEFAULT false NOT NULL,
    tags text DEFAULT ''::text NOT NULL
);


ALTER TABLE public.stores OWNER TO neondb_owner;

--
-- Name: userentity; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.userentity (
    id character varying(255) NOT NULL,
    name character varying(255),
    "emailAddress" character varying(320),
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL,
    "deletedOn" timestamp with time zone
);


ALTER TABLE public.userentity OWNER TO neondb_owner;

--
-- Name: verificationrequests; Type: TABLE; Schema: public; Owner: neondb_owner
--

CREATE TABLE public.verificationrequests (
    id text NOT NULL,
    "sellerId" character varying(255) NOT NULL,
    "businessPermitImageUrl" character varying(500),
    "governmentImageUrl" character varying(500),
    status integer NOT NULL,
    message text,
    "createdAt" timestamp with time zone NOT NULL,
    "updatedAt" timestamp with time zone NOT NULL
);


ALTER TABLE public.verificationrequests OWNER TO neondb_owner;

--
-- Name: __EFMigrationsHistory PK___EFMigrationsHistory; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public."__EFMigrationsHistory"
    ADD CONSTRAINT "PK___EFMigrationsHistory" PRIMARY KEY ("MigrationId");


--
-- Name: analytics PK_analytics; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.analytics
    ADD CONSTRAINT "PK_analytics" PRIMARY KEY (id);


--
-- Name: buyers PK_buyers; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.buyers
    ADD CONSTRAINT "PK_buyers" PRIMARY KEY (id);


--
-- Name: carts PK_carts; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT "PK_carts" PRIMARY KEY (id);


--
-- Name: chats PK_chats; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT "PK_chats" PRIMARY KEY (id);


--
-- Name: followedstores PK_followedstores; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.followedstores
    ADD CONSTRAINT "PK_followedstores" PRIMARY KEY ("buyerId", "storeId");


--
-- Name: likedposts PK_likedposts; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.likedposts
    ADD CONSTRAINT "PK_likedposts" PRIMARY KEY ("buyerId", "postId");


--
-- Name: locations PK_locations; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT "PK_locations" PRIMARY KEY (id);


--
-- Name: messages PK_messages; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT "PK_messages" PRIMARY KEY (id);


--
-- Name: notifications PK_notifications; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT "PK_notifications" PRIMARY KEY (id);


--
-- Name: orderitems PK_orderitems; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orderitems
    ADD CONSTRAINT "PK_orderitems" PRIMARY KEY (id);


--
-- Name: orders PK_orders; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT "PK_orders" PRIMARY KEY (id);


--
-- Name: posts PK_posts; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT "PK_posts" PRIMARY KEY (id);


--
-- Name: products PK_products; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT "PK_products" PRIMARY KEY (id);


--
-- Name: pushtokens PK_pushtokens; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pushtokens
    ADD CONSTRAINT "PK_pushtokens" PRIMARY KEY (id);


--
-- Name: reports PK_reports; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT "PK_reports" PRIMARY KEY (id);


--
-- Name: reviews PK_reviews; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT "PK_reviews" PRIMARY KEY (id);


--
-- Name: sellers PK_sellers; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sellers
    ADD CONSTRAINT "PK_sellers" PRIMARY KEY (id);


--
-- Name: stores PK_stores; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.stores
    ADD CONSTRAINT "PK_stores" PRIMARY KEY (id);


--
-- Name: userentity PK_userentity; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.userentity
    ADD CONSTRAINT "PK_userentity" PRIMARY KEY (id);


--
-- Name: verificationrequests PK_verificationrequests; Type: CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.verificationrequests
    ADD CONSTRAINT "PK_verificationrequests" PRIMARY KEY (id);


--
-- Name: IX_analytics_productId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_analytics_productId" ON public.analytics USING btree ("productId");


--
-- Name: IX_analytics_storeId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_analytics_storeId" ON public.analytics USING btree ("storeId");


--
-- Name: IX_carts_buyerId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_carts_buyerId" ON public.carts USING btree ("buyerId");


--
-- Name: IX_chats_buyerId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_chats_buyerId" ON public.chats USING btree ("buyerId");


--
-- Name: IX_chats_sellerId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_chats_sellerId" ON public.chats USING btree ("sellerId");


--
-- Name: IX_followedstores_storeId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_followedstores_storeId" ON public.followedstores USING btree ("storeId");


--
-- Name: IX_likedposts_postId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_likedposts_postId" ON public.likedposts USING btree ("postId");


--
-- Name: IX_locations_BuyerId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_locations_BuyerId" ON public.locations USING btree ("BuyerId");


--
-- Name: IX_locations_Coordinates; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_locations_Coordinates" ON public.locations USING gist ("Coordinates");


--
-- Name: IX_locations_StoreId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX "IX_locations_StoreId" ON public.locations USING btree ("StoreId") WHERE ("StoreId" IS NOT NULL);


--
-- Name: IX_messages_chatId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_messages_chatId" ON public.messages USING btree ("chatId");


--
-- Name: IX_messages_senderId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_messages_senderId" ON public.messages USING btree ("senderId");


--
-- Name: IX_notifications_userId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_notifications_userId" ON public.notifications USING btree ("userId");


--
-- Name: IX_orderitems_orderId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_orderitems_orderId" ON public.orderitems USING btree ("orderId");


--
-- Name: IX_orderitems_productId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_orderitems_productId" ON public.orderitems USING btree ("productId");


--
-- Name: IX_orders_buyerId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_orders_buyerId" ON public.orders USING btree ("buyerId");


--
-- Name: IX_orders_storeId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_orders_storeId" ON public.orders USING btree ("storeId");


--
-- Name: IX_posts_sellerId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_posts_sellerId" ON public.posts USING btree ("sellerId");


--
-- Name: IX_posts_storeId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_posts_storeId" ON public.posts USING btree ("storeId");


--
-- Name: IX_products_storeId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_products_storeId" ON public.products USING btree ("storeId");


--
-- Name: IX_pushtokens_userId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_pushtokens_userId" ON public.pushtokens USING btree ("userId");


--
-- Name: IX_reports_Buyerid; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_reports_Buyerid" ON public.reports USING btree ("Buyerid");


--
-- Name: IX_reports_reportedPostId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_reports_reportedPostId" ON public.reports USING btree ("reportedPostId");


--
-- Name: IX_reports_reportedProductId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_reports_reportedProductId" ON public.reports USING btree ("reportedProductId");


--
-- Name: IX_reports_reportedStoreId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_reports_reportedStoreId" ON public.reports USING btree ("reportedStoreId");


--
-- Name: IX_reports_reporterId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_reports_reporterId" ON public.reports USING btree ("reporterId");


--
-- Name: IX_reviews_buyerId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_reviews_buyerId" ON public.reviews USING btree ("buyerId");


--
-- Name: IX_reviews_orderId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_reviews_orderId" ON public.reviews USING btree ("orderId");


--
-- Name: IX_reviews_productId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_reviews_productId" ON public.reviews USING btree ("productId");


--
-- Name: IX_stores_sellerId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE UNIQUE INDEX "IX_stores_sellerId" ON public.stores USING btree ("sellerId");


--
-- Name: IX_verificationrequests_sellerId; Type: INDEX; Schema: public; Owner: neondb_owner
--

CREATE INDEX "IX_verificationrequests_sellerId" ON public.verificationrequests USING btree ("sellerId");


--
-- Name: analytics FK_analytics_products_productId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.analytics
    ADD CONSTRAINT "FK_analytics_products_productId" FOREIGN KEY ("productId") REFERENCES public.products(id);


--
-- Name: analytics FK_analytics_stores_storeId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.analytics
    ADD CONSTRAINT "FK_analytics_stores_storeId" FOREIGN KEY ("storeId") REFERENCES public.stores(id);


--
-- Name: buyers FK_buyers_userentity_id; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.buyers
    ADD CONSTRAINT "FK_buyers_userentity_id" FOREIGN KEY (id) REFERENCES public.userentity(id) ON DELETE CASCADE;


--
-- Name: carts FK_carts_buyers_buyerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.carts
    ADD CONSTRAINT "FK_carts_buyers_buyerId" FOREIGN KEY ("buyerId") REFERENCES public.buyers(id) ON DELETE CASCADE;


--
-- Name: chats FK_chats_buyers_buyerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT "FK_chats_buyers_buyerId" FOREIGN KEY ("buyerId") REFERENCES public.buyers(id) ON DELETE CASCADE;


--
-- Name: chats FK_chats_sellers_sellerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.chats
    ADD CONSTRAINT "FK_chats_sellers_sellerId" FOREIGN KEY ("sellerId") REFERENCES public.sellers(id) ON DELETE CASCADE;


--
-- Name: followedstores FK_followedstores_buyers_buyerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.followedstores
    ADD CONSTRAINT "FK_followedstores_buyers_buyerId" FOREIGN KEY ("buyerId") REFERENCES public.buyers(id) ON DELETE CASCADE;


--
-- Name: followedstores FK_followedstores_stores_storeId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.followedstores
    ADD CONSTRAINT "FK_followedstores_stores_storeId" FOREIGN KEY ("storeId") REFERENCES public.stores(id) ON DELETE CASCADE;


--
-- Name: likedposts FK_likedposts_buyers_buyerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.likedposts
    ADD CONSTRAINT "FK_likedposts_buyers_buyerId" FOREIGN KEY ("buyerId") REFERENCES public.buyers(id) ON DELETE CASCADE;


--
-- Name: likedposts FK_likedposts_posts_postId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.likedposts
    ADD CONSTRAINT "FK_likedposts_posts_postId" FOREIGN KEY ("postId") REFERENCES public.posts(id) ON DELETE CASCADE;


--
-- Name: locations FK_locations_buyers_BuyerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT "FK_locations_buyers_BuyerId" FOREIGN KEY ("BuyerId") REFERENCES public.buyers(id) ON DELETE CASCADE;


--
-- Name: locations FK_locations_stores_StoreId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.locations
    ADD CONSTRAINT "FK_locations_stores_StoreId" FOREIGN KEY ("StoreId") REFERENCES public.stores(id) ON DELETE CASCADE;


--
-- Name: messages FK_messages_chats_chatId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT "FK_messages_chats_chatId" FOREIGN KEY ("chatId") REFERENCES public.chats(id) ON DELETE CASCADE;


--
-- Name: messages FK_messages_userentity_senderId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT "FK_messages_userentity_senderId" FOREIGN KEY ("senderId") REFERENCES public.userentity(id) ON DELETE CASCADE;


--
-- Name: notifications FK_notifications_userentity_userId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.notifications
    ADD CONSTRAINT "FK_notifications_userentity_userId" FOREIGN KEY ("userId") REFERENCES public.userentity(id) ON DELETE CASCADE;


--
-- Name: orderitems FK_orderitems_orders_orderId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orderitems
    ADD CONSTRAINT "FK_orderitems_orders_orderId" FOREIGN KEY ("orderId") REFERENCES public.orders(id) ON DELETE CASCADE;


--
-- Name: orderitems FK_orderitems_products_productId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orderitems
    ADD CONSTRAINT "FK_orderitems_products_productId" FOREIGN KEY ("productId") REFERENCES public.products(id) ON DELETE CASCADE;


--
-- Name: orders FK_orders_buyers_buyerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT "FK_orders_buyers_buyerId" FOREIGN KEY ("buyerId") REFERENCES public.buyers(id) ON DELETE CASCADE;


--
-- Name: orders FK_orders_stores_storeId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.orders
    ADD CONSTRAINT "FK_orders_stores_storeId" FOREIGN KEY ("storeId") REFERENCES public.stores(id) ON DELETE CASCADE;


--
-- Name: posts FK_posts_sellers_sellerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT "FK_posts_sellers_sellerId" FOREIGN KEY ("sellerId") REFERENCES public.sellers(id) ON DELETE CASCADE;


--
-- Name: posts FK_posts_stores_storeId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.posts
    ADD CONSTRAINT "FK_posts_stores_storeId" FOREIGN KEY ("storeId") REFERENCES public.stores(id) ON DELETE CASCADE;


--
-- Name: products FK_products_stores_storeId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT "FK_products_stores_storeId" FOREIGN KEY ("storeId") REFERENCES public.stores(id) ON DELETE CASCADE;


--
-- Name: pushtokens FK_pushtokens_userentity_userId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.pushtokens
    ADD CONSTRAINT "FK_pushtokens_userentity_userId" FOREIGN KEY ("userId") REFERENCES public.userentity(id);


--
-- Name: reports FK_reports_buyers_Buyerid; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT "FK_reports_buyers_Buyerid" FOREIGN KEY ("Buyerid") REFERENCES public.buyers(id);


--
-- Name: reports FK_reports_posts_reportedPostId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT "FK_reports_posts_reportedPostId" FOREIGN KEY ("reportedPostId") REFERENCES public.posts(id);


--
-- Name: reports FK_reports_products_reportedProductId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT "FK_reports_products_reportedProductId" FOREIGN KEY ("reportedProductId") REFERENCES public.products(id);


--
-- Name: reports FK_reports_stores_reportedStoreId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT "FK_reports_stores_reportedStoreId" FOREIGN KEY ("reportedStoreId") REFERENCES public.stores(id);


--
-- Name: reports FK_reports_userentity_reporterId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reports
    ADD CONSTRAINT "FK_reports_userentity_reporterId" FOREIGN KEY ("reporterId") REFERENCES public.userentity(id) ON DELETE CASCADE;


--
-- Name: reviews FK_reviews_buyers_buyerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT "FK_reviews_buyers_buyerId" FOREIGN KEY ("buyerId") REFERENCES public.buyers(id) ON DELETE CASCADE;


--
-- Name: reviews FK_reviews_orders_orderId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT "FK_reviews_orders_orderId" FOREIGN KEY ("orderId") REFERENCES public.orders(id);


--
-- Name: reviews FK_reviews_products_productId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.reviews
    ADD CONSTRAINT "FK_reviews_products_productId" FOREIGN KEY ("productId") REFERENCES public.products(id);


--
-- Name: sellers FK_sellers_userentity_id; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.sellers
    ADD CONSTRAINT "FK_sellers_userentity_id" FOREIGN KEY (id) REFERENCES public.userentity(id) ON DELETE CASCADE;


--
-- Name: stores FK_stores_sellers_sellerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.stores
    ADD CONSTRAINT "FK_stores_sellers_sellerId" FOREIGN KEY ("sellerId") REFERENCES public.sellers(id) ON DELETE CASCADE;


--
-- Name: verificationrequests FK_verificationrequests_sellers_sellerId; Type: FK CONSTRAINT; Schema: public; Owner: neondb_owner
--

ALTER TABLE ONLY public.verificationrequests
    ADD CONSTRAINT "FK_verificationrequests_sellers_sellerId" FOREIGN KEY ("sellerId") REFERENCES public.sellers(id) ON DELETE CASCADE;


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON SEQUENCES TO neon_superuser WITH GRANT OPTION;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: public; Owner: cloud_admin
--

ALTER DEFAULT PRIVILEGES FOR ROLE cloud_admin IN SCHEMA public GRANT ALL ON TABLES TO neon_superuser WITH GRANT OPTION;


--
-- PostgreSQL database dump complete
--

\unrestrict xUvLH6ec8qzWe0u9pkY32mcmKMduVipqYjbeGDzg1MSHhKvr3nm9AhIzf0LIDJn

