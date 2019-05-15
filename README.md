## C/C++扩展Python

主要整理自[SegmentFault](https://segmentfault.com/a/1190000000479951)

### 1. 使用Python-C-API

C-API是使用Python包裹C最底层的方法，主要依赖于python安装目录下的`Python.h`，如果使用Anaconda，具体目录是`$ANACONDA_HOME/include/pythonX.X/Python.h`，后面会看到，其实在build的时候把这个目录加进了-I选项中，因此在.c文件中可以直接使用include<Python.h>引入。

C-API把所有的python对象都使用PyObject表示，再通过定义init函数等，最后使用python自带的`distutils`中的Extension和setup来编译，`distutils`是Python中自带的编译c的方法，通常把setup代码写在`build.py`或者`setup.py`，然后运行`python setup.py build_ext --inplace`来完成编译，具体的代码如下，使用c调用math.h中的cos方法来计算余弦函数：

```C
/*  Example of wrapping cos function from math.h with the Python-C-API. */
// cos_module.c

#include <Python.h>
#include <math.h>

/*  wrapped cosine function */
static PyObject* cos_func(PyObject* self, PyObject* args)
{
    double value;
    double answer;

    /*  parse the input, from python float to c double */
    if (!PyArg_ParseTuple(args, "d", &value))
        return NULL;
    /* if the above function returns -1, an appropriate Python exception will
     * have been set, and the function simply returns NULL
     */

    /* call cos from libm */
    answer = cos(value);

    /*  construct the output from cos, from c double to python float */
    return Py_BuildValue("f", answer);
}

/*  define functions in module 
    [function_name, function, args, docs]
*/
static PyMethodDef CosMethods[] =
{
     {"cos_func", cos_func, METH_VARARGS, "evaluate the cosine"},
     {NULL, NULL, 0, NULL}
};

/* module initialization */
PyMODINIT_FUNC

initcos_module(void)
{
     (void) Py_InitModule("cos_module", CosMethods);
}
```

有几个地方需要注意：

1. initxxx(): 这个方法是当python引入这个so包的时候，调用的文档，函数名等，主要是为了python模块的初始化，暴露那些接口，类似于python中的__init__.py的功能，在这里，`cos_module`是module名字，cos_func是module中的一个对象，只暴露其中的cos_func方法
2. 使用C-API的方法的扩展性比较差，在Python2，3之间不通用，最直接的原因是Py_InitModule在3的Python.h没有该方法，取而代之的是Py_InitModule3，而且接口并不完全一样，因此这里只能使用python2编译

接下来需要一个`setup.py`：

```python
from distutils.core import setup, Extension

# define the extension module
cos_module = Extension('cos_module', sources=['cos_module.c'])

# run the setup
setup(ext_modules=[cos_module])
```

Extension自身还有很多选项，例如gcc中的-I，功能`include_dirs=[numpy.get_include()]`等等。这里就不展开了，基本上gcc能设置的选项在Extension初始化中都可以加入，没有设置的就是默认值，接下来运行`python setup.py build_ext --inplace`，输出完整的gcc命令，我们分析一下是如何完成编译的：


```shell
gcc -pthread 
-B /usr/share/Anaconda2/compiler_compat 
-Wl,--sysroot=/ -fno-strict-aliasing 
-g 
-O2 -DNDEBUG -g -fwrapv -O3 -Wall -Wstrict-prototypes 
-fPIC 
-I/usr/share/Anaconda2/include/python2.7 
-c c_api_cos.c 
-o build/temp.linux-x86_64-2.7/c_api_cos.o
```

在gcc中加入了-I选项，-c表示只编译生成.o文件，-fPIC表示生成动态链接库

```shell
gcc -pthread -shared \
-B /usr/share/Anaconda2/compiler_compat \
-L/usr/share/Anaconda2/lib \
-Wl,-rpath=/usr/share/Anaconda2/lib \
-Wl,--no-as-needed \
-Wl,--sysroot=/ \
build/temp.linux-x86_64-2.7/c_api_cos.o \
-L/usr/share/Anaconda2/lib \
-lpython2.7 \
-o /home/xxx/tmp/cpython/c-api/cos_module.so
```

链接动态库，libpython2.7.so，在-L/usr/share/Anaconda2/lib中寻找，用-lpython2.7寻找libpython2.7.so

### ctypes

ctypes是python内置的包，可以通过引用ctypes来生成c数据类型，自带的cdll用于加载c语言编译出的动态链接库(.so)，在python端，我们可以通过调用函数接口的形式包装c语言编译出来的so文件。

接下来展示so文件的调用过程

首先是用于编译so文件的c代码func.c：

```python
#include "math.h"

double cos_func(double a) {
	return cos(a);
}
```

然后将其编译为so文件：

```shell
$ gcc func.c -shared -fPIC -o libcos.so -lm func.c
```

在当前目录产生一个libcos.so，注意这里要加一个-lm选项，是为了把静态库libm.a，也就是math.h对应的实现引进来。

接下来使用cos.py包裹刚才编译好的so文件：

```python
# wrap c funciton
from ctypes import *
from ctypes.util import find_library
    
# method1: lib = cdll.LoadLibrary(find_library('cos'))
# method2: lib = cdll.LoadLibrary('libcos.so')
lib = CDLL('libcos.so') # 以上两种方法都可以加载动态库
    
lib.cos_func.argtypes = [c_double] # 定义函数的输入参数
lib.cos_func.restype = c_double # 定义函数的输出参数
    
def cos_func(x):
   x = c_double(x)
   return lib.cos_func(x)
```

要注意的就是在加载完so以后，其实python是不知道函数的定义的，也就是输入参数和返回值的类型都必须由python手动指定，上面代码中的`argtypes`和`restype`就是为了这个。在完成这个之后，就可以在别的py中`from cos import cos_func`来使用这个包裹函数。

### Ctypes与Python类型对应

ctypes的中内置了基本的C类型，包括`c_int`,`c_float`,`c_double`等等，这里有一张对应表：

![](http://princepicbed.oss-cn-beijing.aliyuncs.com/blog_20180828214008.png)

可以使用`x = ctypes.cast(0.5,c_float)`来进行转换，需要注意的是，经常使用的python字符串在python2里面是ascii码，但是在python3中string默认编码是utf-8，直接使用`ctypes.cast(s, c_char_p])`会失败，因此需要先把s编码为ascii然后再进行转换，或者使用b'Hello'这样的二进制字符串也是可以的。

#### ctypes中使用结构体

有时候在ctypes中需要使用结构体，这个时候，我们需要在python中先声明一下这个结构体，然后就可以像普通的c类型一样使用这个结构体了，下面是官网的一个例子：

首先C代码中给出某个结构体的定义：
```C
typedef Struct{
    int x;
    int y;
} POINT;
```

在Python中声明这个结构体：
```python
from ctypes import *
class POINT(Structure):
   _fields_ = [("x", c_int), #在这里声明结构体中的域
               ("y", c_int)]
point = POINT(10, 20)
```

如果有使用到结构体，需要像上一小节一样，使用`lib.cos_func.argtypes`和`lib.cos_func.restype`设置到参数和返回值类型中，最后调用。

#### Ctypes总结

使用Ctypes扩展python的好处在于，在C端是纯粹的C，没有和python挂钩的其他包（如果有用到Numpy之类的包除外），这种方法的扩展性比较好，python2，python3通用，不过需要自己手动设定参数和返回值，比较麻烦，尤其是c文件中如果涉及结构体，指针等操作，声明起来工作量非常大。所以推荐如果是已经有了一个so，希望使用ctypes包裹的话，还是先用c包装一下，暴露出比较简明的接口，比如字符串，整型的api，然后再使用c去调用，这样能够有效降低python端的工作量。

### Cython

Cython的原理其实和第一种方法C-API非常相似，实质上Cython是一种特殊的语法，包含了python的全部语法，并使用一些类c的语法对python进行扩展，比如cdef，cimport等等，其原理就是把pyx脚本编译为C-API描述的c语言，然后再把c语言使用第一小节讲到的方法编译成so，使python能够直接import，以下是一个比较简单的`cos_module.pyx`:

```python
""" Example of wrapping cos function from math.h using Cython. """

cdef extern from "math.h":
    double cos(double arg)

def cos_func(arg):
    return cos(arg)
```

然后通过一个`setup.py`编译，注意这里使用了Cython.Distutils中的build_ext

```python
from distutils.core import setup, Extension
from Cython.Distutils import build_ext

setup(
    cmdclass={'build_ext': build_ext},
    ext_modules=[Extension("cos_module", ["cos_module.pyx"])]
)
```
和第一小节一样，使用`python setup.py build_ext --inplace`来编译，我们看一下编译的输出：

```shell
running build_ext
cythoning cos_module.pyx to cos_module.c # 这里把cython编译为c
building 'cos_module' extension
gcc -pthread -B /usr/share/Anaconda3/compiler_compat -Wl,--sysroot=/ -Wsign-compare -DNDEBUG -g -fwrapv -O3 -Wall -Wstrict-prototypes -fPIC -I/usr/share/Anaconda3/include/python3.6m -c cos_module.c -o build/temp.linux-x86_64-3.6/cos_module.o # 编译.o中间文件
gcc -pthread -shared -B /usr/share/Anaconda3/compiler_compat -L/usr/share/Anaconda3/lib -Wl,-rpath=/usr/share/Anaconda3/lib -Wl,--no-as-needed -Wl,--sysroot=/ build/temp.linux-x86_64-3.6/cos_module.o -L/usr/share/Anaconda3/lib -lpython3.6m -o /home/xxx/tmp/cpython/cython/cos_module.cpython-36m-x86_64-linux-gnu.so # 编译最终的.so文件
```

与第一小节最明显的差别在于，使用cython方法会先在当前目录编译出一个cos_module.c，这个c文件里面的内容是比较难懂的，不过如果仔细读他，可以发现本质上就是使用了C-API，最后再按照C-API的编译方法，把c编译为一个python可读的so，最后，和第一小节一样执行`from cos_module import cos_func`就可以了。

### 可视化Cython加速

通过`cython -a cos_module.pyx`命令可以获得一个`cos_module.html`文件，打开这个文件，可以看到颜色越黄，这个地方就和python的交互越多，性能也就越差（这个例子比较简单，所以效果不明显）

![](http://oodo7tmt3.bkt.clouddn.com/blog_20180828212556.png)

### Cython踩坑

这里还有一个坑，就是setup.py中的module名称必须和pyx的文件名一致，Extension("cos_module", ["cos_module.pyx"])，否则编译没有问题，但是在运行时刻会报错

```
dynamic module does not define module export function (XXX)
```

### Cython和NumPy

由于工作中经常使用Numpy，大部分时候向量化的重复操作，如矩阵求he等等都可以用Numpy进行，而且速度也非常之快，但一些时候在面对强依赖的循环并涉及大量单个元素的操作的时候（一个例子就是目标检测算法中的非极大值抑制算法），Numpy就显得力不从心了，这个时候，使用Cython加速往往是一个不错的选择。因此本节说一下如何在Cython加速Numpy。

核心思想是将Numpy array变为一个连续的存储，比如一个np.array(dtype=int)，就把它变成C语言的int []，然后写一个c函数，通过pyx文件调用这个函数，其中最关键的语句是`np.PyArray_DATA(in_array)`，将numpy array变成指针的过程。接下来我们实现刚才的cos_func对一个数组操作的代码：

1. 首先写一个c，我们让他的输入是一个double的数组in_array，然后给出一个输出是out_array，也是一个数组（这是c语言风格的返回方法），然后给定数组的长度，实现起来很容易，对数组的每一个元素操作就可以了。

```c
#include <math.h>

/*  Compute the cosine of each element in in_array, storing the result in
 *  out_array. */
void cos_doubles(double * in_array, double * out_array, int size){
    int i;
    for(i=0;i<size;i++){
        out_array[i] = cos(in_array[i]);
    }
}
```

2. 别忘了要写一个头文件`cos_doubles.h`

```c
void cos_doubles(double * in_array, double * out_array, int size);
```

3. 通过Cython引入这个c函数

```cython
""" Example of wrapping a C function that takes C double arrays as input using
    the Numpy declarations from Cython """

# import both numpy and the Cython declarations for numpy
import numpy as np
cimport numpy as np

# if you want to use the Numpy-C-API from Cython
# (not strictly necessary for this example)
np.import_array()

# cdefine the signature of our c function
cdef extern from "cos_doubles.h": # 调用一下刚才写的头文件定义函数声明
    void cos_doubles (double * in_array, double * out_array, int size)

# create the wrapper code, with numpy type annotations
def cos_doubles_func(np.ndarray[double, ndim=1, mode="c"] in_array not None,
                     np.ndarray[double, ndim=1, mode="c"] out_array not None):
    
    # 使用np.PyArray_DATA()把numpy的数据转换为一个指针传给c函数，注意numpy的类型匹配
    cos_doubles(<double*> np.PyArray_DATA(in_array),
                <double*> np.PyArray_DATA(out_array),
                in_array.shape[0])
```

4. 通过`setup.py`编译

```python
from distutils.core import setup, Extension
import numpy
from Cython.Distutils import build_ext

setup(
    cmdclass={'build_ext': build_ext},
    ext_modules=[Extension("cos_doubles",
                 sources=["_cos_doubles.pyx", "cos_doubles.c"], # 这里写上c的源文件路径
                 include_dirs=[numpy.get_include()])],  # 由于这里需要引入numpy的一些库，所以这里必须加上include_dir=[numpy.get_include()]，相当于gcc -I XXX 的功能
)
```

最后就是和上面一样执行build_ext就能获得一个`cos_doubles`的python module，通过`cos_doubles.cos_doubles_func(input, output)`来调用这个python函数，达到加速的目的。

### 总结

C语言扩展python用到的4种比较常用的技术：

- C-Api
- ctypes
- SWIG
- Cython

其中SWIG本篇笔记中没有记录，可能以后还会补充，在这里只展示了如何扩展最简单的接口，在科学计算中，常常使用c来加速比较耗时的矩阵运算。这就涉及到numpy的c扩展，这几种方法都可以扩展numpy，但是这几种方法各有优缺点，比如C-API无法在python的不同版本直接使用，需要修改c代码，ctypes容易发生动态错误，而且错误提示没有其他几种方法鲁棒。Cython需要学习新的语法等等。

总体来说，Cython的可用性是最强的，推荐使用Cython的方法来扩展python



