#ifndef TEST_EGL_H
#define TEST_EGL_H
typedef void *EGLContext;
#define EGL_NO_CONTEXT ((EGLContext)0)
EGLContext eglGetCurrentContext(void);
#endif
