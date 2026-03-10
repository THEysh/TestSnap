## 4.2.1等波纹低通滤波器原型

对二元组间低通滤波器原型，推导出归一化元件L和C的值。假设端阻抗是1Ω，截止频率为ω0的二阶低通滤波器的功率损耗比为

$$P _ { L R } = 1 + k ^ { 2 } T _ { N } ^ { 2 } ( a )$$

式中，$1+k^{2}$是通带的波纹高度。切比雪夫多项式有下面的特性：

$$T _ { N } ( 0 ) = \left\{ \begin{array} { l l } { { 0 , } } & { { N \mathrm { ~ i s ~ o d d ~ } } } \\ { { 1 , } } & { { N \mathrm { ~ i s ~ e v e n ~ } } } \end{array} \right.$$

在$\alpha=0$处，N为奇数，滤波器功率损耗比为1。但在$\alpha=1$时，N为偶数时，功率损耗比为1+K^2

当N=2时，滤波器的输入阻抗为

$$Z _ { a } = j \omega L + \frac { R ( 1 - j \omega R C ) } { 1 + \omega ^ { 2 } R ^ { 2 } C ^ { 2 } }$$

因为

所以功率损耗比能表示为

$$\Gamma=\frac{Z_{in}-1}{Z_{in}+1}$$

$$p _ { L R } = \frac { 1 } { 1 - | \Gamma | ^ { 2 } } = 1 - \frac { 1 } { \left[ \left( Z _ { \mathrm { i n } } - 1 \right) \left( Z _ { \mathrm { i n } } ^ { * } - 1 \right) \right] \left[ \left( Z _ { \mathrm { i n } } ^ { * } - 1 \right) \left( Z _ { \mathrm { i n } } ^ { * } + 1 \right) \right] } = \frac { \left( Z _ { \mathrm { i n } } + 1 \right) ^ { 2 } } { 2 \left( Z _ { \mathrm { i n } } + Z _ { \mathrm { i n } } ^ { * } \right) }$$

$$Z _ { + } + Z _ { - } = \frac { 2 R } { 1 - R ^ { 2 } / R _ { C } ^ { 2 } }$$

$$\left|Z_{m}\right|^{2}=\left(\frac{R}{1+\omega^{2}R^{2}C^{2}}\right)^{2}+\omega^{2}L^{2}\left(\frac{\omega CR}{1+\omega^{2}R^{2}C^{2}}\right)^{2}$$

经过一系列计算，最后

$$P _ { L , a } = \frac { 1 + \omega ^ { 2 } R ^ { 2 } C ^ { 2 } } { 4 R } \left[ \frac { R } { 1 + \omega ^ { 2 } R ^ { 2 } C ^ { 2 } } + 1 \right] ^ { 2 } + \left( \omega L - \frac { \omega C R ^ { 2 } } { 1 + \omega ^ { 2 } R ^ { 2 } C ^ { 2 } } \right) ^ { 2 } ]$$ $$= 1 + \frac { 1 } { 4 R } \left[ ( 1 - R ^ { 2 } ) + ( R ^ { 2 } C ^ { 2 } + L ^ { 2 } - 2 L C R ^ { 2 } ) \omega ^ { 2 } + L ^ { 2 } C ^ { 2 } R ^ { 2 } \omega ^ { 4 } \right]$$

因为

$$T _ { 2 } ( x ) = 2 x ^ { 2 } - 1$$

所以

$$1 + k ^ { 2 } ( 4 \omega ^ { 4 } - 4 \omega ^ { 3 } + 1 ) = 1 + \frac { 1 } { 4 R } \Big [ - ( R ^ { 2 } ) ^ { 2 } + ( R ^ { 2 } C ^ { 2 } + L ^ { 2 } - 2 L C R ^ { 2 } ) \omega ^ { 2 } + L ^ { 2 } C ^ { 2 } R ^ { 2 } \omega ^ { 4 } \Big ]$$

在$ω=0$处就可以对R,L,C求解

$$R = 1 + 2 k ^ { 2 } \pm 2 k \sqrt { 1 + k ^ { 2 } } , \; \; ( N \mathrm { ~ f o r ~ e v e n ~ } )$$

