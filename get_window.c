#include <Carbon/Carbon.h>

int main(int a, char **b) {
        ProcessSerialNumber psn = { 0L, 0L };
        OSStatus err = GetFrontProcess(&psn);

        CFStringRef processName = NULL;
        err = CopyProcessName(&psn, &processName);
        printf("%s\n", CFStringGetCStringPtr(processName, NULL));
        CFRelease(processName);
}
