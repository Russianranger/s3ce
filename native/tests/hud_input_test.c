#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "../hud_input.c"

int main(void) {
    const size_t length = 0x169000;
    const uintptr_t gateway=0x21000001;
    enum { FIXED_COUNT=sizeof(fixed_corrections)/sizeof(fixed_corrections[0]),
           CORRECTION_COUNT=FIXED_COUNT+3 };
    struct correction corrections[CORRECTION_COUNT];
    memcpy(corrections,fixed_corrections,sizeof(fixed_corrections));
    corrections[FIXED_COUNT]=(struct correction){0x107844u,0xe1a00004u,0xe59fc000u};
    corrections[FIXED_COUNT+1]=(struct correction){0x107848u,status_hit[(0x107848-0x107834)/4],0xe12fff3cu};
    corrections[FIXED_COUNT+2]=(struct correction){0x10784cu,0xe88d0041u,(uint32_t)gateway};
    unsigned char *code=malloc(length), *before=malloc(length);
    assert(code && before);
    memset(code, 0xa5, length);
    for(size_t i=0;i<sizeof(profile)/sizeof(profile[0]);++i)
        memcpy(code+profile[i].offset,profile[i].words,profile[i].length);
    memcpy(before,code,length);
    assert(s3ce_patch_hud_input(NULL,length,NULL,CODE_EXTENT,gateway)==0);
    assert(s3ce_patch_hud_input(code,CODE_EXTENT-1,code,CODE_EXTENT-1,gateway)==0);
    assert(s3ce_patch_hud_input(code,length,code+4,CODE_EXTENT,gateway)==0);
    assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT-1,gateway)==0);
    assert(s3ce_patch_hud_input(code,length,code,length+1,gateway)==0);
    assert(s3ce_patch_hud_input(code+1,length-1,code+1,CODE_EXTENT,gateway)==0);
    void *overflow=(void *)(UINTPTR_MAX&~(uintptr_t)3);
    assert(s3ce_patch_hud_input(overflow,length,overflow,CODE_EXTENT,gateway)==0);
    assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT,0)==0);
    assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT,gateway-1)==0);
#if UINTPTR_MAX > UINT32_MAX
    assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT,(uintptr_t)UINT32_MAX+2)==0);
#endif
    assert(!memcmp(code,before,length));
    for(size_t i=0;i<sizeof(profile)/sizeof(profile[0]);++i)
        for(size_t j=0;j<profile[i].length;++j){
            code[profile[i].offset+j]^=1;
            assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT,gateway)==-1);
            code[profile[i].offset+j]^=1;
        }
    for(size_t i=0;i<sizeof(corrections)/sizeof(corrections[0]);++i){
        memcpy(code+corrections[i].offset,&corrections[i].after,4);
        assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT,gateway)==-1);
        memcpy(code,before,length);
    }
    assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT,gateway)==1);
    for(size_t i=0;i<sizeof(corrections)/sizeof(corrections[0]);++i)
        memcpy(before+corrections[i].offset,&corrections[i].after,4);
    assert(!memcmp(code,before,length));
    assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT,gateway)==2);
    assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT,gateway+4)==-1);
    for(size_t i=0;i<sizeof(corrections)/sizeof(corrections[0]);++i){
        for(size_t j=0;j<4;++j){
            code[corrections[i].offset+j]^=1;
            assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT,gateway)==-1);
            code[corrections[i].offset+j]^=1;
        }
        memcpy(code+corrections[i].offset,&corrections[i].before,4);
        assert(s3ce_patch_hud_input(code,length,code,CODE_EXTENT,gateway)==-1);
        memcpy(code,before,length);
    }
    free(code);free(before);
    puts("HUD input guards: five instructions and bounded status gateway, atomic profile refusal, bounds and idempotence PASS");
}
