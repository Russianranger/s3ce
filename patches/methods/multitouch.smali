.method public static onTouchEvent(Lcom/ideaworks3d/airplay/AirplayView;Landroid/view/MotionEvent;)Z
    .locals 8
    # S3CE: Android pointer IDs identify fingers; coordinate APIs take indices.
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getActionMasked()I
    move-result v0
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getPointerCount()I
    move-result v1
    packed-switch v0, :s3ce_actions
    goto :s3ce_done

    :s3ce_down
    const/4 v3, 0x4
    goto :s3ce_indexed
    :s3ce_up
    const/4 v3, 0x5
    :s3ce_indexed
    invoke-virtual {p1}, Landroid/view/MotionEvent;->getActionIndex()I
    move-result v2
    if-ge v2, v1, :s3ce_done
    invoke-virtual {p1, v2}, Landroid/view/MotionEvent;->getPointerId(I)I
    move-result v4
    invoke-virtual {p1, v2}, Landroid/view/MotionEvent;->getX(I)F
    move-result v5
    float-to-int v5, v5
    invoke-virtual {p1, v2}, Landroid/view/MotionEvent;->getY(I)F
    move-result v6
    float-to-int v6, v6
    invoke-virtual {p0, v4, v3, v5, v6}, Lcom/ideaworks3d/airplay/AirplayView;->onMotionEvent(IIII)V
    goto :s3ce_done

    :s3ce_move
    const/4 v3, 0x6
    goto :s3ce_each
    :s3ce_cancel
    # Cancellation must release every active finger, just like ACTION_UP.
    const/4 v3, 0x5
    :s3ce_each
    const/4 v2, 0x0
    :s3ce_loop
    if-ge v2, v1, :s3ce_done
    invoke-virtual {p1, v2}, Landroid/view/MotionEvent;->getPointerId(I)I
    move-result v4
    invoke-virtual {p1, v2}, Landroid/view/MotionEvent;->getX(I)F
    move-result v5
    float-to-int v5, v5
    invoke-virtual {p1, v2}, Landroid/view/MotionEvent;->getY(I)F
    move-result v6
    float-to-int v6, v6
    invoke-virtual {p0, v4, v3, v5, v6}, Lcom/ideaworks3d/airplay/AirplayView;->onMotionEvent(IIII)V
    add-int/lit8 v2, v2, 0x1
    goto :s3ce_loop
    :s3ce_done
    const/4 v0, 0x1
    return v0
    :s3ce_actions
    .packed-switch 0x0
        :s3ce_down
        :s3ce_up
        :s3ce_move
        :s3ce_cancel
        :s3ce_done
        :s3ce_down
        :s3ce_up
    .end packed-switch
.end method
