from __future__ import with_statement

import unittest
import datetime
import time
import random

from flask import Flask
from flaskext.cache import Cache

class CacheTestCase(unittest.TestCase):
    
    def setUp(self):
        app = Flask(__name__)
        
        app.debug = False
        app.config['CACHE_TYPE'] = 'simple'
        
        self.cache = Cache()
        self.cache.init_app(app)
        
        self.app = app
        
    def tearDown(self):
        self.app = None
        self.cache = None
        self.tc = None

    def test_00_set(self):
        self.cache.set('hi', 'hello')
        
        assert self.cache.get('hi') == 'hello'
        
    def test_01_add(self):
        self.cache.add('hi', 'hello')
        
        assert self.cache.get('hi') == 'hello'
        
        self.cache.add('hi', 'foobar')
        
        assert self.cache.get('hi') == 'hello'
    
    def test_02_delete(self):
        self.cache.set('hi', 'hello')
        
        self.cache.delete('hi')
        
        assert self.cache.get('hi') is None
        
    def test_03_cached_view(self):
        
        @self.app.route('/')
        @self.cache.cached(5)
        def cached_view():
            return str(time.time())
        
        tc = self.app.test_client()
        
        rv = tc.get('/')
        the_time = rv.data
        
        time.sleep(2)
        
        rv = tc.get('/')
        
        assert the_time == rv.data
        
        time.sleep(5)
        
        rv = tc.get('/')
        assert the_time != rv.data
        
    def test_04_cached_view_unless(self):        
        @self.app.route('/a')
        @self.cache.cached(5, unless=lambda: True)
        def non_cached_view():
            return str(time.time())
        
        @self.app.route('/b')
        @self.cache.cached(5, unless=lambda: False)
        def cached_view():
            return str(time.time())
                
        tc = self.app.test_client()
        
        rv = tc.get('/a')
        the_time = rv.data
        
        time.sleep(1)
        
        rv = tc.get('/a')
        assert the_time != rv.data
        
        rv = tc.get('/b')
        the_time = rv.data
        
        time.sleep(1)
        rv = tc.get('/b')
        
        assert the_time == rv.data
        
    def test_05_cached_function(self):
        
        with self.app.test_request_context():
            @self.cache.cached(2, key_prefix='MyBits')
            def get_random_bits():
                return [random.randrange(0, 2) for i in range(50)]
    
            my_list = get_random_bits()
            his_list = get_random_bits()
            
            assert my_list == his_list
            
            time.sleep(4)
            
            his_list = get_random_bits()
            
            assert my_list != his_list
    
    def test_06_memoize(self):
        
        with self.app.test_request_context():
            @self.cache.memoize(5)
            def big_foo(a, b):
                return a+b+random.randrange(0, 100000)
            
            result = big_foo(5, 2)
            
            time.sleep(1)
            
            assert big_foo(5, 2) == result
            
            result2 = big_foo(5, 3)
            assert result2 != result
            
            time.sleep(4)
            
            assert big_foo(5, 2) != result
            assert big_foo(5, 3) == result2
            
            time.sleep(1)
            
            assert big_foo(5, 3) != result2
            
    def test_07_delete_memoize(self):
        
        with self.app.test_request_context():
            @self.cache.memoize(5)
            def big_foo(a, b):
                return a+b+random.randrange(0, 100000)
            
            result = big_foo(5, 2)
            
            time.sleep(1)
            
            assert big_foo(5, 2) == result
            assert big_foo(5, 2) == result
            assert big_foo(5, 3) != result
            
            self.cache.delete_memoized('big_foo')
            
            assert big_foo(5, 2) != result


    def test_08_delete_memoize(self):

        with self.app.test_request_context():
            @self.cache.memoize()
            def big_foo(a, b):
                return a+b+random.randrange(0, 100000)

            result_a = big_foo(5, 1)
            result_b = big_foo(5, 2)

            assert big_foo(5, 1) == result_a
            assert big_foo(5, 2) == result_b

            self.cache.delete_memoized('big_foo', 5, 2)

            assert big_foo(5, 1) == result_a
            assert big_foo(5, 2) != result_b

    def test_09_args_memoize(self):
    
        with self.app.test_request_context():
            @self.cache.memoize()
            def big_foo(a, b):
                return sum(a)+sum(b)+random.randrange(0, 100000)
            
            result_a = big_foo([5,3,2], [1])
            result_b = big_foo([3,3], [3,1])
            
            assert big_foo([5,3,2], [1]) == result_a
            assert big_foo([3,3], [3,1]) == result_b
            
            self.cache.delete_memoized('big_foo', [5,3,2], [1])
            
            assert big_foo([5,3,2], [1]) != result_a
            assert big_foo([3,3], [3,1]) == result_b
            
    def test_10_kwargs_memoize(self):
        
        with self.app.test_request_context():
            @self.cache.memoize()
            def big_foo(a, b=None):
                return a+sum(b.values())+random.randrange(0, 100000)
            
            result_a = big_foo(1, dict(one=1,two=2))
            result_b = big_foo(5, dict(three=3,four=4))
            
            assert big_foo(1, dict(one=1,two=2)) == result_a
            assert big_foo(5, dict(three=3,four=4)) == result_b
            
            self.cache.delete_memoized('big_foo', 1, dict(one=1,two=2))
            
            assert big_foo(1, dict(one=1,two=2)) != result_a
            assert big_foo(5, dict(three=3,four=4)) == result_b

    def test_11_cache_key_property(self):
        @self.app.route('/')
        @self.cache.cached(5)
        def cached_view():
            return str(time.time())

        assert hasattr(cached_view, "make_cache_key")
        assert callable(cached_view.make_cache_key)

        tc = self.app.test_client()
        
        rv = tc.get('/')
        the_time = rv.data

        with self.app.test_request_context():
            cache_data = self.cache.get(cached_view.make_cache_key())
            assert the_time == cache_data

    def test_12_make_cache_key_function_property(self):
        @self.app.route('/<foo>/<bar>')
        @self.cache.memoize(5)
        def cached_view(foo, bar):
            return str(time.time())

        assert hasattr(cached_view, "make_cache_key")
        assert callable(cached_view.make_cache_key)

        tc = self.app.test_client()
        
        rv = tc.get('/a/b')
        the_time = rv.data

        cache_key = cached_view.make_cache_key(foo=u"a", bar=u"b")
        cache_data = self.cache.get(cache_key)
        assert the_time == cache_data

        different_key = cached_view.make_cache_key(foo=u"b", bar=u"a")
        different_data = self.cache.get(different_key)
        assert the_time != different_data

    def test_13_cache_timeout_property(self):
        @self.app.route('/')
        @self.cache.memoize(5)
        def cached_view1():
            return str(time.time())

        @self.app.route('/<foo>/<bar>')
        @self.cache.memoize(10)
        def cached_view2(foo, bar):
            return str(time.time())

        assert hasattr(cached_view1, "cache_timeout")
        assert hasattr(cached_view2, "cache_timeout")
        assert cached_view1.cache_timeout == 5
        assert cached_view2.cache_timeout == 10

        # test that this is a read-write property
        cached_view1.cache_timeout = 2
        cached_view2.cache_timeout = 3

        assert cached_view1.cache_timeout == 2
        assert cached_view2.cache_timeout == 3

        tc = self.app.test_client()

        rv1 = tc.get('/')
        time1 = rv1.data
        time.sleep(1)
        rv2 = tc.get('/a/b')
        time2 = rv2.data

        # VIEW1
        # it's been 1 second, cache is still active
        assert time1 == tc.get('/').data
        time.sleep(2)
        # it's been 3 seconds, cache is not still active
        assert time1 != tc.get('/').data

        # VIEW2
        # it's been 2 seconds, cache is still active
        assert time2 == tc.get('/a/b').data
        time.sleep(2)
        # it's been 4 seconds, cache is not still active
        assert time2 != tc.get('/a/b').data

if __name__ == '__main__':
    unittest.main()
